"""Download and verify versioned demo assets; no credentials required."""
import json
from pathlib import Path
import urllib.request

try:
    from .media_release import ASSETS, digest, verify_release
except ImportError:
    from media_release import ASSETS, digest, verify_release

HERE = Path(__file__).resolve().parents[1]
BASE = 'https://github.com/imhaojie/PitchPrism/releases/download/v1.0.0/'


def fetch():
    lock = json.loads((HERE / 'data/media-lock.json').read_text())
    if set(lock) != set(ASSETS):
        raise ValueError('Media lock must list exactly the three public assets')
    build = HERE / 'build'
    build.mkdir(exist_ok=True)
    for name, expected in lock.items():
        target = build / name
        if target.is_file() and digest(target) == expected:
            continue
        temporary = target.with_suffix('.download')
        try:
            with urllib.request.urlopen(BASE + name, timeout=90) as response, temporary.open('wb') as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            if digest(temporary) != expected:
                raise ValueError('Release asset hash mismatch: ' + name)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    verify_release(build, HERE / 'data')
    print('Published match media and player timing verified')


if __name__ == '__main__':
    fetch()
