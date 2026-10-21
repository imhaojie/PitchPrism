"""Export the original GameBuddy shell with the same materialized clip observations."""
import argparse
import itertools
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from product.football.clip import CLIP,local_story,snapshot


def export_demo(target):
    source=ROOT/'product/football'
    shutil.copytree(source/'watch',target,dirs_exist_ok=True,ignore=shutil.ignore_patterns('node_modules','package*.json','tests','__pycache__'))
    for module in ['media','stage','adapters','court','config','glass','navigation','annotations','content','dev','companions','vendor']:
        shutil.copytree(ROOT/'product/watch'/module,target/'shared'/module,dirs_exist_ok=True,ignore=shutil.ignore_patterns('*.test.js'))
    for name in ['source.mp4','enhanced.mp4','manifest.json']:
        path=source/'build'/name
        if not path.is_file():raise RuntimeError('Render the media before export; missing '+name)
        (target/'media').mkdir(exist_ok=True);shutil.copy2(path,target/'media'/name)
    manifest=json.loads((source/'build/manifest.json').read_text())
    if manifest.get('source',{}).get('sha256')!=CLIP['source']['sha256'] or manifest.get('dataSha256')!=__import__('hashlib').sha256((source/'data/clip.json').read_bytes()).hexdigest():
        raise RuntimeError('Media manifest is stale or belongs to a different source')
    states=[snapshot(o['second']) for o in CLIP['observations']];stories={}
    for index,state in enumerate(states):
        for mode,player in itertools.product(['casual','analyst'],['all',*[p['id'] for p in CLIP['roster']]]):
            stories[f'{index}|{mode}|all|{player}']=local_story(state,mode,'all',player)
    (target/'demo-data.json').write_text(json.dumps(dict(match=CLIP,states=states,stories=stories),ensure_ascii=False,separators=(',',':')))
    (target/'transport.js').write_text((target/'transport.js').read_text().replace('const STATIC_DEMO=false;','const STATIC_DEMO=true;'))
    (target/'.nojekyll').touch();print(f'Exported {len(states)} reviewed states and {len(stories)} local explanations to {target}')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/'product/football/build/site');export_demo(parser.parse_args().out)
