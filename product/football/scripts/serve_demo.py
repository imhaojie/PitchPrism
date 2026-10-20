"""Preview the static export with the same Range implementation as production."""
import argparse
from pathlib import Path
import sys
from urllib.parse import urlsplit, unquote

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from product.football.server import Handler, ThreadingHTTPServer

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=4181)
args = parser.parse_args()
base = Path(__file__).resolve().parents[1] / 'build'


class StaticHandler(Handler):
    def do_GET(self):
        path = (base / unquote(urlsplit(self.path).path).lstrip('/')).resolve()
        if path.is_dir():
            path /= 'index.html'
        if not path.is_relative_to(base) or not path.is_file():
            return self.send_error(404)
        self.send_file(path)


print(f'Static export: http://127.0.0.1:{args.port}/site/', flush=True)
ThreadingHTTPServer(('127.0.0.1', args.port), StaticHandler).serve_forever()
