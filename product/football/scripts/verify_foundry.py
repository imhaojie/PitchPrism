"""Real cloud smoke test; refuses to treat a local template as a model result."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from product.football.server import MATCH, load_env
from product.football.analytics import snapshot
from product.football.foundry import run_agent, settings

parser = argparse.ArgumentParser()
parser.add_argument('--env-file', default='.env')
parser.add_argument('--out', default='artifacts/foundry-live.json')
args = parser.parse_args()
load_env(args.env_file)
if not settings()['configured']:
    sys.exit('NOT VERIFIED: Azure endpoint, deployment and identity are required. No model call made.')
state = snapshot(MATCH, 45)
result = run_agent(state, mode='analyst')
if result['provider'] != 'azure-foundry' or not result.get('trace'):
    sys.exit('NOT VERIFIED: no live Foundry tool trace')
receipt = {'verifiedAt': datetime.now(timezone.utc).isoformat(), 'synthetic': True,
           'sourceSha256': hashlib.sha256(json.dumps(MATCH, sort_keys=True).encode()).hexdigest(), 'result': result}
target = Path(args.out); target.parent.mkdir(exist_ok=True, parents=True)
target.write_text(json.dumps(receipt, indent=2) + '\n')
print(f'VERIFIED: actual Foundry response, {len(result["trace"])} tool steps; receipt: {target}')
