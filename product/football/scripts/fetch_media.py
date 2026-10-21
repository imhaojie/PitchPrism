"""Fetch the frozen demo release with source/data/media SHA-256 checks (no credentials)."""
import hashlib
import json
from pathlib import Path
import urllib.request
HERE=Path(__file__).resolve().parents[1]
BASE='https://github.com/imhaojie/PitchPrism/releases/download/football-match-v2/'


def fetch():
    lock=json.loads((HERE/'data/media-lock.json').read_text());build=HERE/'build';build.mkdir(exist_ok=True)
    for name,expected in lock.items():
        target=build/name
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest()!=expected:
            with urllib.request.urlopen(BASE+name,timeout=90) as response:
                temporary=target.with_suffix('.download');temporary.write_bytes(response.read())
            if hashlib.sha256(temporary.read_bytes()).hexdigest()!=expected:
                temporary.unlink();raise ValueError('Release asset hash mismatch: '+name)
            temporary.replace(target)
    manifest=json.loads((build/'manifest.json').read_text());clip=json.loads((HERE/'data/clip.json').read_text())
    if manifest['source']['sha256']!=clip['source']['sha256'] or manifest['dataSha256']!=hashlib.sha256((HERE/'data/clip.json').read_bytes()).hexdigest():
        raise ValueError('Released media does not match the reviewed observations')
    print('Frozen real-match media verified')

if __name__=='__main__':fetch()
