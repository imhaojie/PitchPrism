"""Export PitchPrism with the exact released media and reviewed observations."""
import argparse
import itertools
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from product.football.clip import CLIP, local_story, snapshot
from product.football.scripts.media_release import ASSETS, verify_release

SHARED = ['media', 'stage', 'adapters', 'court', 'config', 'glass', 'navigation',
          'annotations', 'content', 'dev', 'companions', 'vendor']


def export_demo(target):
    source = ROOT / 'product/football'
    target = target.resolve()
    if target == source or source in target.parents and not target.is_relative_to(source / 'build'):
        raise ValueError('Export into the build directory or an external destination')
    # Verify before writing anything into the public export.
    verify_release(source / 'build', source / 'data')
    shutil.copytree(source / 'watch', target, dirs_exist_ok=True,
        ignore=shutil.ignore_patterns('node_modules', 'package*.json', 'tests', '__pycache__'))
    for module in SHARED:
        shutil.copytree(ROOT / 'product/watch' / module, target / 'shared' / module,
            dirs_exist_ok=True, ignore=shutil.ignore_patterns('*.test.js'))
    (target / 'media').mkdir(exist_ok=True)
    for name in ASSETS:
        shutil.copy2(source / 'build' / name, target / 'media' / name)
    states = [snapshot(observation['second']) for observation in CLIP['observations']]
    stories = {}
    for index, state in enumerate(states):
        for mode, player in itertools.product(['casual', 'analyst'], ['all', *[p['id'] for p in CLIP['roster']]]):
            stories[f'{index}|{mode}|all|{player}'] = local_story(state, mode, 'all', player)
    (target / 'demo-data.json').write_text(json.dumps(
        dict(match=CLIP, states=states, stories=stories), ensure_ascii=False, separators=(',', ':')))
    transport, count = re.subn(r'const STATIC_DEMO\s*=\s*false;', 'const STATIC_DEMO = true;',
        (target / 'transport.js').read_text(), count=1)
    if count != 1:
        raise RuntimeError('Static transport switch was not found')
    (target / 'transport.js').write_text(transport)
    (target / '.nojekyll').touch()
    print(f'Exported {len(states)} reviewed states and {len(stories)} local explanations to {target}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'product/football/build/site')
    export_demo(parser.parse_args().out)
