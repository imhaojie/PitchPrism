"""Original synthetic football footage and timed enhanced MP4. Requires Pillow + FFmpeg.

The software scene is an editorial simulation; no optical tracking is performed.
The source/output mapping follows the existing GameBuddy dual-timeline contract.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parents[1]))
from product.football.analytics import local_story, snapshot

MATCH = json.loads((HERE / "data/match.json").read_text())
W, H, FPS = 960, 540, 24
COLORS = {"NBR": "#dcff8c", "RIV": "#b2adfc"}


def font(size):
    for file in ["/System/Library/Fonts/Supplemental/DIN Alternate Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if Path(file).is_file():
            return ImageFont.truetype(file, size)
    return ImageFont.load_default()


def project(x, y):
    # Perspective projection from normalized synthetic pitch coordinates.
    depth = y / 100
    return (185 + (70 - 185) * depth + (610 + 210 * depth) * x / 100,
            142 + depth * 330)


def background():
    image = Image.new("RGB", (W, H), "#101e1e")
    draw = ImageDraw.Draw(image)
    rng = random.Random(24)
    for y in range(125):
        draw.line((0, y, W, y), fill=(20 + y // 9, 32 + y // 9, 34 + y // 10))
    for _ in range(6500):
        x, y = rng.randrange(W), rng.randrange(25, 119)
        shade = rng.choice(["#303b3b", "#4c5550", "#727469", "#8a9184", "#bbc0a5", "#554964"])
        draw.rectangle((x, y, x + 1, y + 1), fill=shade)
    draw.rectangle((0, 119, W, 137), fill="#172527")
    for x in range(10, 940, 150):
        draw.text((x, 122), "PITCHPRISM   /   EVERY ANGLE", font=font(9), fill="#c7dba7")
    # Grass stripes follow pitch coordinates, with a worn centre and fine mowing texture.
    draw.polygon([project(0, 0), project(100, 0), project(100, 100), project(0, 100)], fill="#30584a")
    for i in range(10):
        draw.polygon([project(i * 10, 0), project((i + 1) * 10, 0), project((i + 1) * 10, 100), project(i * 10, 100)],
                     fill="#386351" if i % 2 else "#315b4a")
    for _ in range(15000):
        x, y = rng.uniform(0, 100), rng.uniform(0, 100)
        px, py = project(x, y)
        draw.point((px, py), fill=rng.choice(["#406754", "#345b4c", "#2e5547", "#436d58"]))

    def line(points, width=2):
        draw.line([project(x, y) for x, y in points], fill="#b6c7b0", width=width)

    line([(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)])
    line([(50, 0), (50, 100)])
    for x, sign in [(0, 1), (100, -1)]:
        line([(x, 20), (x + sign * 16, 20), (x + sign * 16, 80), (x, 80)])
        line([(x, 36), (x + sign * 5, 36), (x + sign * 5, 64), (x, 64)])
        px, py = project(x + sign * 11, 50)
        draw.ellipse((px - 2, py - 1, px + 2, py + 1), fill="#bdcbb3")
        # Perspective goal frames and net: original generated shapes.
        a, b = project(x, 44), project(x, 56)
        dx = -20 if x == 0 else 20
        draw.polygon([a, b, (b[0] + dx, b[1] - 26), (a[0] + dx, a[1] - 26)], fill="#c2d2c040", outline="#d7e1d0")
        for j in range(1, 7):
            f = j / 7
            draw.line((a[0] + dx * f, a[1] - 26 * f, b[0] + dx * f, b[1] - 26 * f), fill="#799084")
        draw.line((a[0], a[1], a[0], a[1] - 28, b[0], b[1] - 28, b[0], b[1]), fill="#e1e8d6", width=2)
    points = [project(50 + 9.15 / 105 * 100 * math.cos(i * math.pi / 90), 50 + 9.15 / 68 * 100 * math.sin(i * math.pi / 90)) for i in range(181)]
    draw.line(points, fill="#b6c7b0", width=2)
    px, py = project(50, 50)
    draw.ellipse((px - 2, py - 1, px + 2, py + 1), fill="#d5dcc6")
    draw.rectangle((0, 503, W, H), fill="#101e1e")
    for x in range(0, W, 15):
        draw.line((x, 507, x + 4, 535), fill="#273635", width=4)
    return image


BASE = background()


def positions(second):
    result = {}
    for p in MATCH["roster"]:
        keys = [(0, p["position"])]
        for e in MATCH["events"]:
            if e["playerId"] == p["id"]:
                keys.append((e["second"], e["start"]))
            if e.get("recipientId") == p["id"]:
                keys.append((e["second"] + 1.6, e["end"]))
        keys.sort()
        before = max((k for k in keys if k[0] <= second), default=keys[0], key=lambda k: k[0])
        after = min((k for k in keys if k[0] > second), default=before, key=lambda k: k[0])
        ratio = (second - before[0]) / (after[0] - before[0]) if after[0] > before[0] else 0
        result[p["id"]] = [before[1][i] + ratio * (after[1][i] - before[1][i]) for i in (0, 1)]
    return result


def draw_frame(second, enhanced=False, output_second=None):
    frame = BASE.copy()
    draw = ImageDraw.Draw(frame)
    events = [e for e in MATCH["events"] if e["second"] <= second]
    current = events[-1] if events else None
    pos = positions(second)
    if enhanced and current:
        recent = [e for e in events if e["type"] == "pass" and second - e["second"] <= 8]
        for e in recent:
            a, b = project(*e["start"]), project(*e["end"])
            draw.line((a, b), fill="#dfff83", width=3)
            draw.ellipse((b[0] - 7, b[1] - 4, b[0] + 7, b[1] + 4), outline="#dfff83", width=2)
    roster = sorted(MATCH["roster"], key=lambda p: pos[p["id"]][1])
    for p in roster:
        x, y = project(*pos[p["id"]])
        scale = .7 + pos[p["id"]][1] / 190
        h, w = 24 * scale, 6 * scale
        swing = math.sin(second * 9 + p["number"]) * 3 * scale
        draw.ellipse((x - w * 2, y - 2, x + w * 2, y + 5), fill="#254b3e")
        # Boots, shorts, running arms, shirt and head.
        draw.line((x - 2 * scale, y - 8 * scale, x - 3 * scale - swing, y), fill="#d7b7a0", width=max(2, int(3 * scale)))
        draw.line((x + 2 * scale, y - 8 * scale, x + 3 * scale + swing, y), fill="#d7b7a0", width=max(2, int(3 * scale)))
        draw.line((x - w, y - h + 7 * scale, x - w - 3 * scale, y - 10 * scale + swing), fill="#d7b7a0", width=2)
        draw.line((x + w, y - h + 7 * scale, x + w + 3 * scale, y - 10 * scale - swing), fill="#d7b7a0", width=2)
        draw.rounded_rectangle((x - w, y - h + 5 * scale, x + w, y - 8 * scale), radius=2, fill=COLORS[p["team"]])
        draw.rectangle((x - w, y - 10 * scale, x + w, y - 6 * scale), fill="#192d28" if p["team"] == "NBR" else "#e0dff1")
        draw.ellipse((x - 3 * scale, y - h - 2 * scale, x + 3 * scale, y - h + 5 * scale), fill="#cfaa8f")
        draw.arc((x - 3 * scale, y - h - 2 * scale, x + 3 * scale, y - h + 4 * scale), 180, 360, fill="#272b26", width=2)
        if enhanced and current and p["id"] in {current["playerId"], current.get("recipientId")}:
            draw.ellipse((x - 12, y - 5, x + 12, y + 7), outline=COLORS[p["team"]], width=2)
            name = p["name"].split()[-1].upper()
            length = draw.textlength(name, font=font(12))
            draw.rounded_rectangle((x - length / 2 - 6, y - h - 28, x + length / 2 + 6, y - h - 8), radius=4, fill="#142724")
            draw.text((x - length / 2, y - h - 26), name, fill="#eff3de", font=font(12))
    if current:
        ratio = min(1, (second - current["second"]) / 1.6)
        ball = [current["start"][i] + ratio * (current["end"][i] - current["start"][i]) for i in (0, 1)]
        x, y = project(*ball)
        lift = math.sin(ratio * math.pi) * (14 if current["type"] in {"pass", "shot"} else 0)
        draw.ellipse((x - 4, y, x + 5, y + 4), fill="#1e4036")
        draw.ellipse((x - 3, y - 5 - lift, x + 3, y + 1 - lift), fill="#fff9dc", outline="#384b3e")
    draw.rounded_rectangle((28, 22, 235, 49), radius=5, fill="#142422")
    draw.text((39, 29), "SYNTHETIC MATCH SIMULATION", font=font(11), fill="#cad9bd")
    if enhanced:
        label = "TACTICAL PAUSE" if 20 <= output_second < 24 or output_second >= 60 else "REPLAY" if output_second >= 52 else "ENHANCED VIEW"
        draw.rounded_rectangle((755, 22, 932, 49), radius=5, fill="#dcff8c")
        draw.text((769, 29), label, font=font(12), fill="#203427")
        if current:
            draw.rounded_rectangle((28, 445, 452, 494), radius=8, fill="#142622")
            headline = local_story(snapshot(MATCH, second))["headline"]
            draw.text((42, 454), headline, font=font(17), fill="#f2f2db")
            draw.text((42, 477), f'{current["id"]}   /   EDITORIAL OVERLAY   /   SYNTHETIC COORDINATES', font=font(9), fill="#b9c9b3")
    return frame


def source_time(output):
    timeline = MATCH["production"]["timeline"]
    segment = next((s for s in timeline if s["outputStart"] <= output < s["outputEnd"]), timeline[-1])
    ratio = max(0, min(1, (output - segment["outputStart"]) / (segment["outputEnd"] - segment["outputStart"])))
    return segment["sourceStart"] + ratio * (segment["sourceEnd"] - segment["sourceStart"])


def render(enhanced, out):
    duration = 64 if enhanced else 48
    command = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", f"{W}x{H}",
               "-framerate", str(FPS), "-i", "-", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", str(duration),
               "-c:v", "libx264", "-preset", "fast", "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", str(out)]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        for index in range(duration * FPS):
            output_second = index / FPS
            second = source_time(output_second) if enhanced else output_second
            process.stdin.write(draw_frame(second, enhanced, output_second).tobytes())
    finally:
        process.stdin.close()
    if process.wait():
        raise RuntimeError("FFmpeg render failed")
    # Full decode, not just container metadata.
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(out), "-f", "null", "-"], check=True)
    return {"path": out.name, "sha256": hashlib.sha256(out.read_bytes()).hexdigest(), "durationSeconds": duration,
            "width": W, "height": H, "fps": FPS, "fullDecode": True, "audio": "silent stereo track; no real match audio"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--poster-only", action="store_true")
    args = parser.parse_args()
    out = HERE / "build"
    out.mkdir(exist_ok=True)
    draw_frame(29, enhanced=True, output_second=33).save(HERE / "watch/poster.jpg", quality=92)
    if not args.poster_only:
        outputs = [render(False, out / "source.mp4"), render(True, out / "enhanced.mp4")]
        record = {"synthetic": True, "renderer": "original Pillow software scene + FFmpeg",
                  "modelUsedForRender": False, "notTracking": True, "outputs": outputs,
                  "timeline": MATCH["production"]["timeline"], "dataSha256": hashlib.sha256((HERE / "data/match.json").read_bytes()).hexdigest()}
        (out / "manifest.json").write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps(record, indent=2))
