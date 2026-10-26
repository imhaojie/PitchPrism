"""Minimal, explicit Content Safety check of one existing English tactical caption.

Does not run Foundry or modify the reviewed film. A receipt is written only after
the actual Azure adapter succeeds. No credentials or endpoint are printed.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from product.football import azure_services
from product.football.server import load_env


def verify():
    script = json.loads((ROOT / 'product/football/data/tactical-story.json').read_text())
    step = script['scenes']['build']['steps'][0]
    text = {'headline': step['title'], 'explanation': step['text']}
    if not azure_services.enabled('CONTENT_SAFETY'):
        raise RuntimeError('Enable Content Safety explicitly before live verification')
    result = azure_services.moderate_story(text)
    if result.get('status') != 'passed':
        raise RuntimeError('Content Safety did not return a successful analysis')
    return {'verifiedAt': datetime.now(timezone.utc).isoformat(), 'service': 'Azure AI Content Safety',
        'scope': 'One existing English tactical caption; not generative match inference',
        'textSha256': hashlib.sha256((text['headline'] + '\n' + text['explanation']).encode()).hexdigest(),
        'result': result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', default='.env')
    parser.add_argument('--run', action='store_true', help='Send one caption to the configured Azure service')
    parser.add_argument('--out', type=Path, default=Path('artifacts/content-safety-live.json'))
    args = parser.parse_args()
    if not args.run:
        print('No request made. Add --run to analyze one English caption through the configured service.')
        return
    load_env(args.env_file)
    result = verify()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n'); os.chmod(args.out, 0o600)
    print('VERIFIED: Azure Content Safety analyzed one English tactical caption; receipt:', args.out)


if __name__ == '__main__':
    try: main()
    except (RuntimeError, azure_services.AzureServiceError) as error: sys.exit(str(error))
