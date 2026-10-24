"""Standard-library verification shared by release fetching and static export."""
import hashlib
import json
from pathlib import Path

ASSETS = ('manifest.json', 'source.mp4', 'enhanced.mp4')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_manifest(manifest, clip, data_sha256, media_lock):
    if manifest.get('source', {}).get('sha256') != clip['source']['sha256'] or manifest.get('dataSha256') != data_sha256:
        raise ValueError('Released media does not match the reviewed observations')
    if manifest.get('timeline') != clip['production']['timeline'] or manifest.get('durationSeconds') != clip['production']['durationSeconds']:
        raise ValueError('Player timeline differs from the released movie')
    if manifest.get('outputSha256') != media_lock['enhanced.mp4']:
        raise ValueError('Manifest output identity differs from the media lock')


def verify_release(build, data):
    lock = json.loads((data / 'media-lock.json').read_text())
    if set(lock) != set(ASSETS):
        raise ValueError('Media lock must list exactly the three public assets')
    for name, expected in lock.items():
        if digest(build / name) != expected:
            raise ValueError('Release asset hash mismatch: ' + name)
    manifest = json.loads((build / 'manifest.json').read_text())
    clip_path = data / 'clip.json'
    verify_manifest(manifest, json.loads(clip_path.read_text()), digest(clip_path), lock)
    return manifest
