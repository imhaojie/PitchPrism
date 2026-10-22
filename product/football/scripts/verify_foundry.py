"""Real cloud smoke test for the active clip or separate synthetic fixture."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from product.football import clip
from product.football.analytics import snapshot
from product.football.foundry import run_agent, settings
from product.football.server import MATCH, load_env


def verify(scenario='clip', second=None, mode='analyst'):
    if not settings()['configured']:
        raise RuntimeError('NOT VERIFIED: Azure endpoint, deployment and identity are required. No model call made.')
    if scenario == 'clip':
        state = clip.snapshot(37.8 if second is None else second)
        context = clip.AGENT_CONTEXT
        source_hash = clip.CLIP['source']['sha256']
        data_hash = hashlib.sha256((ROOT / 'product/football/data/clip.json').read_bytes()).hexdigest()
    elif scenario == 'synthetic':
        state = snapshot(MATCH, 45 if second is None else second)
        context = None
        source_hash = hashlib.sha256(json.dumps(MATCH, sort_keys=True).encode()).hexdigest()
        data_hash = source_hash
    else:
        raise ValueError('Unknown scenario')
    result = run_agent(state, mode=mode, context=context)
    trace = result.get('trace', [])
    successful = {step['tool'] for step in trace if step.get('ok')}
    if result['provider'] != 'azure-foundry' or not {'read_match_state', 'read_evidence', 'validate_story'} <= successful:
        raise RuntimeError('NOT VERIFIED: no successful read/inspect/validate Foundry trace')
    return {'verifiedAt': datetime.now(timezone.utc).isoformat(), 'scenario': scenario,
            'synthetic': state['synthetic'], 'sourceSecond': state['sourceSecond'],
            'sourceSha256': source_hash, 'dataSha256': data_hash, 'result': result}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--env-file', default='.env')
    parser.add_argument('--scenario', choices=['clip', 'synthetic'], default='clip')
    parser.add_argument('--second', type=float)
    parser.add_argument('--mode', choices=['casual', 'analyst'], default='analyst')
    parser.add_argument('--out', type=Path, default=Path('artifacts/foundry-live.json'))
    args = parser.parse_args()
    load_env(args.env_file)
    receipt = verify(args.scenario, args.second, args.mode)
    args.out.parent.mkdir(exist_ok=True, parents=True)
    args.out.write_text(json.dumps(receipt, indent=2) + '\n')
    os.chmod(args.out, 0o600)
    print(f'VERIFIED: actual Foundry response for {receipt["scenario"]} at {receipt["sourceSecond"]}s; '
          f'{len(receipt["result"]["trace"])} tool steps; receipt: {args.out}')


if __name__ == '__main__':
    try:
        main()
    except RuntimeError as error:
        sys.exit(str(error))
