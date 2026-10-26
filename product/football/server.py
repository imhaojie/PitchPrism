"""One-process demo API and static delivery. Deploy the same app on Container Apps."""
import argparse
from collections import OrderedDict, deque
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import threading
import time
from urllib.parse import parse_qs, urlsplit

from .analytics import local_story, snapshot, validate_match
from .foundry import FoundryError, run_agent, settings
from . import clip
from . import azure_services

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
MATCH = validate_match(json.loads((HERE / "data/match.json").read_text()))
CACHE, CALLS, LOCK = OrderedDict(), deque(), threading.Lock()


def load_env(path):
    # Deliberately does not execute shell syntax or print secrets.
    if path and Path(path).is_file():
        for line in Path(path).read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, sep, value = line.partition("=")
            if sep and key.startswith(("AZURE_", "PITCHPRISM_")):
                os.environ.setdefault(key, value.strip().strip("\"'"))


def validate_options(body):
    second = body.get("second", 0)
    state = snapshot(MATCH, second)
    mode, team, player = (body.get(k, default) for k, default in [("mode", "casual"), ("team", "all"), ("player", "all")])
    if mode not in {"casual", "analyst"} or team not in {"all", "NBR", "RIV"} or player not in {"all", *[p["id"] for p in MATCH["roster"]]}:
        raise ValueError("Invalid audience, team or player")
    return state, mode, team, player


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Do not log user query strings, auth headers or model payloads.
        if args and str(args[0]).startswith('"POST'):
            return

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self'; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'self'")
        super().end_headers()

    def send_json(self, data, status=200):
        raw = json.dumps(data, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        url = urlsplit(self.path)
        try:
            if url.path == "/api/health":
                config = settings()
                return self.send_json({"ok": True, "service": "PitchPrism", "synthetic": False,
                    "foundryConfigured": config["configured"], "foundryVerified": False,
                    "provider": "azure-foundry" if config["configured"] else "local",
                    "azureServices": azure_services.status(),
                    "mediaReady": (HERE / "build/enhanced.mp4").is_file()})
            if url.path == "/api/match":
                return self.send_json(MATCH)
            if url.path == '/api/clip':
                return self.send_json(clip.CLIP)
            if url.path == '/api/clip/snapshot':
                return self.send_json(clip.snapshot(float(parse_qs(url.query).get('t', [0])[0])))
            if url.path == "/api/snapshot":
                second = float(parse_qs(url.query).get("t", [0])[0])
                return self.send_json(snapshot(MATCH, second))
            if url.path == "/api/recap":
                state = snapshot(MATCH, MATCH["durationSeconds"])
                return self.send_json({"scope": state["scope"], "stats": state["stats"],
                    "story": local_story(state), "synthetic": True})
        except (ValueError, FoundryError) as error:
            return self.send_json({"error": str(error)}, 400)
        if url.path.startswith("/api/"):
            return self.send_json({"error": "Not found"}, 404)
        # Static allowlist excludes the cloned historical data, deployment files and local secrets.
        from urllib.parse import unquote
        decoded = unquote(url.path)
        shared = {'media','stage','adapters','court','config','glass','navigation','annotations','content','dev','companions','vendor'}
        if '..' in decoded.split('/') or (decoded.startswith('/shared/') and decoded.split('/')[2] not in shared):
            return self.send_error(404)
        if decoded.startswith('/media/') and decoded not in {'/media/source.mp4','/media/enhanced.mp4','/media/manifest.json'}:
            return self.send_error(404)
        routes = [("/shared/", ROOT / "product/watch"), ("/shared/media/", ROOT / "product/watch/media"),
                  ("/shared/stage/", ROOT / "product/watch/stage"),
                  ("/shared/adapters/", ROOT / "product/watch/adapters"),
                  ("/media/", HERE / "build"), ("/", HERE / "watch")]
        for prefix, base in routes:
            if url.path.startswith(prefix):
                relative = url.path[len(prefix):] or "index.html"
                path = (base / relative).resolve()
                if not path.is_relative_to(base.resolve()) or not path.is_file() or path.suffix not in {".html", ".css", ".js", ".json", ".svg", ".woff2", ".ttf", ".webp", ".mp4", ".jpg", ".png"}:
                    return self.send_error(404)
                return self.send_file(path)

    def send_file(self, path):
        size, start, end = path.stat().st_size, 0, path.stat().st_size - 1
        range_header = self.headers.get("Range")
        if range_header:
            import re
            match = re.fullmatch(r"bytes=(\d+)-(\d*)", range_header)
            if not match:
                return self.send_error(416)
            start = int(match[1])
            end = min(size - 1, int(match[2])) if match[2] else size - 1
            if start > end or start >= size:
                return self.send_error(416)
        self.send_response(206 if range_header else 200)
        self.send_header("Content-Type", mimetypes.guess_type(path)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache")
        if range_header:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        try:
            with path.open("rb") as stream:
                stream.seek(start)
                remaining = end - start + 1
                while remaining > 0:
                    chunk = stream.read(min(65536, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        if self.path not in {"/api/explain", '/api/clip/explain'}:
            return self.send_json({"error": "Not found"}, 404)
        # Browser requests must come from this host. CLI/API tests need no Origin.
        origin = self.headers.get("Origin")
        if origin and urlsplit(origin).netloc != self.headers.get("Host"):
            return self.send_json({"error": "Cross-origin request rejected"}, 403)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 4096:
                raise ValueError("Body must be between 1 and 4096 bytes")
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("JSON body must be an object")
            is_clip = self.path == '/api/clip/explain'
            if is_clip:
                state = clip.snapshot(body.get('second', 0))
                mode, team, player = body.get('mode', 'casual'), body.get('team', 'all'), body.get('player', 'all')
                if mode not in {'casual', 'analyst'} or team not in {'all', 'MCI', 'NEW'} or player not in {'all', *[p['id'] for p in clip.CLIP['roster']]}:
                    raise ValueError('Invalid clip audience or role')
            else:
                state, mode, team, player = validate_options(body)
            if body.get("provider", "local") == "local":
                return self.send_json((clip.local_story if is_clip else local_story)(state, mode, team, player))
            if body.get("provider") != "azure-foundry":
                raise ValueError("Unsupported provider")
            if not settings()["configured"]:
                return self.send_json({"error": "Foundry is not configured. Local evidence mode remains available."}, 503)
        except (ValueError, TypeError, FoundryError) as error:
            return self.send_json({"error": str(error)}, 400)
        if not LOCK.acquire(blocking=False):
            return self.send_json({"error": "A Foundry explanation is already running. Please retry shortly."}, 429)
        try:
            cache_key = (state['matchId'], round(state["sourceSecond"], 1), mode, team, player)
            if cache_key in CACHE:
                return self.send_json({**CACHE[cache_key], "cached": True})
            now = time.monotonic()
            while CALLS and now - CALLS[0] > 3600:
                CALLS.popleft()
            if len(CALLS) >= int(os.environ.get("PITCHPRISM_MAX_AI_CALLS_HOUR", "12")):
                return self.send_json({"error": "Demo's hourly model budget reached. Use local evidence mode."}, 429)
            CALLS.append(now)
            result = run_agent(state, mode, team, player, context=clip.AGENT_CONTEXT if is_clip else None)
            result = azure_services.enrich_cloud_result(result)
            CACHE[cache_key] = result
            while len(CACHE) > 128:
                CACHE.popitem(last=False)
            self.send_json(result)
        except (FoundryError, azure_services.AzureServiceError) as error:
            self.send_json({"error": str(error), "provider": "azure-foundry", "verified": False}, 502)
        finally:
            LOCK.release()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4180)
    parser.add_argument("--env-file", default=".env")
    args = parser.parse_args()
    load_env(args.env_file)
    azure_services.load_key_vault_secret()
    server = ThreadingHTTPServer((args.host, args.port), partial(Handler, directory=str(HERE / "watch")))
    print(f"PitchPrism: http://{args.host}:{args.port} | reviewed match excerpt | Foundry configured: {settings()['configured']}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
