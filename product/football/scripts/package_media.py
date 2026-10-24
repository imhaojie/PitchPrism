"""Promote a reviewed render into the demo's hash-locked release assets.

Does not render, infer, upload, or change the reviewed video bytes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reviewed_content(clip):
    # Production timing and presentation labels can evolve; evidence cannot.
    content = {k: v for k, v in clip.items() if k not in {'production', 'scenes'}}
    content['scenes'] = [dict(id=s['id'], second=s['second'], clock=s['clock'],
        analysis=s['analysis'], casual=s['casual'], routes=s['routes'],
        players=[{k: v for k, v in p.items() if k != 'label'} for p in s['players']])
        for s in clip['scenes']]
    return content


def package(video, receipt, review_input, destination):
    manifest = json.loads(receipt.read_text())
    clip_path = HERE / 'data/clip.json'
    clip = json.loads(clip_path.read_text())
    original = json.loads(review_input.read_text())
    source_lock = json.loads((HERE / 'data/source-lock.json').read_text())
    if digest(video) != manifest['outputSha256']:
        raise ValueError('Reviewed output hash mismatch')
    if digest(review_input) != manifest['clipDataSha256'] or reviewed_content(original) != reviewed_content(clip):
        raise ValueError('Reviewed observations or anchors changed since this render')
    if manifest['source']['sha256'] != clip['source']['sha256'] or manifest['timeline'] != clip['production']['timeline']:
        raise ValueError('Source identity or player timeline differs from the reviewed render')
    if manifest['storySha256'] != digest(HERE / 'data/tactical-story.json'):
        raise ValueError('Burned-in readings differ from the current editorial story')
    if digest(HERE / 'build/source.mp4') != source_lock['remuxSha256']:
        raise ValueError('Source remux hash mismatch')
    if not manifest['fullVideoAudioDecode'] or not manifest['completeSourceRetained']:
        raise ValueError('Reviewed render lacks decode/source coverage proof')
    destination.mkdir(parents=True, exist_ok=True)
    for source, name in [(video, 'enhanced.mp4'), (HERE / 'build/source.mp4', 'source.mp4')]:
        if source.resolve() != (destination / name).resolve():
            shutil.copy2(source, destination / name)
    manifest['output'] = 'enhanced.mp4'
    manifest['dataSha256'] = digest(clip_path)
    manifest['publication'] = {'version': clip['production']['version'],
        'renderInputDataSha256': manifest['clipDataSha256'],
        'note': 'The original reviewed render is byte-identical. Player timing and role labels match the reviewed movie; evidence and anchors are unchanged.'}
    manifest['textAudit']['fonts'] = [Path(name).name for name in manifest['textAudit']['fonts']]
    (destination / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    lock = {name: digest(destination / name) for name in ['manifest.json', 'source.mp4', 'enhanced.mp4']}
    (HERE / 'data/media-lock.json').write_text(json.dumps(lock, indent=2) + '\n')
    print('Packaged verified media; no video re-encoding. Publish all three release assets together.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', required=True, type=Path)
    parser.add_argument('--receipt', required=True, type=Path)
    parser.add_argument('--review-input', required=True, type=Path)
    parser.add_argument('--out', type=Path, default=HERE / 'build')
    args = parser.parse_args()
    package(args.video, args.receipt, args.review_input, args.out)
