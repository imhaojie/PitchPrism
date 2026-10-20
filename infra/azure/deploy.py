#!/usr/bin/env python3
"""Explicit subscription target, quota-aware Foundry deployment, optional Container Apps.

Default is a read-only plan. --apply creates the displayed resources. Never upgrades
a trial, creates a subscription, registers paid marketplace offers or exposes keys.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def az(*args):
    result = subprocess.run(['az', *args, '--only-show-errors', '-o', 'json'], text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip()[-1800:])
    return json.loads(result.stdout) if result.stdout.strip() else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--subscription', required=True, help='Explicit subscription ID; never implicit/default')
    parser.add_argument('--location', default='eastus2')
    parser.add_argument('--group', default='pitchprism-demo')
    parser.add_argument('--model', default='gpt-4.1-mini')
    parser.add_argument('--image', default='', help='Optional public container image')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    account = az('account', 'show', '--subscription', args.subscription)
    if account.get('state') != 'Enabled':
        raise RuntimeError('The explicitly selected subscription is not Enabled')
    models = az('cognitiveservices', 'model', 'list', '--location', args.location, '--subscription', args.subscription)
    candidates = [m for m in models if m.get('model', {}).get('name') == args.model and
                  any(s.get('name') == 'GlobalStandard' for s in m.get('model', {}).get('skus', []))]
    if not candidates:
        raise RuntimeError('Requested model/GlobalStandard is unavailable in this subscription/region. Select an available model and region; no deployment was attempted.')
    chosen = sorted(candidates, key=lambda m: m['model']['version'])[-1]['model']
    plan = {'subscription': args.subscription, 'group': args.group, 'region': args.location,
            'model': chosen['name'], 'version': chosen['version'], 'throughput': 'GlobalStandard capacity=1',
            'container': args.image or 'not requested', 'replicas': '0–1, 0.25 vCPU / 0.5 GiB',
            'notes': 'Usage consumes credits or incurs charges. Trial/region/model quota can prevent deployment. This is not a cost guarantee.'}
    print(json.dumps(plan, indent=2))
    if not args.apply:
        print('Read-only plan. Add --apply only after checking the target subscription and remaining trial credit.')
        return
    for namespace in ['Microsoft.CognitiveServices', *(['Microsoft.App'] if args.image else [])]:
        az('provider', 'register', '--namespace', namespace, '--wait', '--subscription', args.subscription)
    az('group', 'create', '--name', args.group, '--location', args.location, '--subscription', args.subscription,
       '--tags', 'project=PitchPrism', 'purpose=hackathon-demo')
    deployment = az('deployment', 'group', 'create', '--name', 'pitchprism', '--resource-group', args.group,
        '--subscription', args.subscription, '--template-file', str(Path(__file__).with_name('main.bicep')),
        '--parameters', f'modelName={chosen["name"]}', f'modelVersion={chosen["version"]}', f'containerImage={args.image}')
    outputs = {key: value['value'] for key, value in deployment['properties']['outputs'].items()}
    user = az('ad', 'signed-in-user', 'show')
    az('role', 'assignment', 'create', '--assignee-object-id', user['id'], '--assignee-principal-type', 'User',
       '--role', 'Cognitive Services OpenAI User', '--scope', outputs['foundryResourceId'], '--subscription', args.subscription)
    receipt = ROOT / 'artifacts/azure-deployment.json'
    receipt.parent.mkdir(exist_ok=True)
    receipt.write_text(json.dumps(outputs, indent=2) + '\n')
    env = ROOT / '.env'
    if env.exists():
        print('Existing .env preserved. Configure it from artifacts/azure-deployment.json.')
    else:
        env.write_text(f'AZURE_OPENAI_ENDPOINT={outputs["endpoint"]}\nAZURE_OPENAI_DEPLOYMENT={outputs["modelDeployment"]}\nAZURE_USE_ENTRA=1\nPITCHPRISM_MAX_AI_CALLS_HOUR=12\n')
        os.chmod(env, 0o600)
    print('Deployed; keyless local configuration is ready or preserved. Allow a few minutes for RBAC propagation, then run verify_foundry.py.')
    if outputs.get('demoUrl'):
        print(outputs['demoUrl'])


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, KeyError) as error:
        sys.exit(str(error))
