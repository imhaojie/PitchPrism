"""Opt-in Azure service adapters. Disabled adapters never acquire tokens or use the network.

Transport tests are not evidence of a live Azure deployment. Endpoints and secrets
stay server-side; storage/monitoring never receive the video, prompts or prose.
"""
from datetime import datetime, timezone
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid


class AzureServiceError(RuntimeError):
    pass


def endpoint(value, suffix):
    parsed = urllib.parse.urlsplit(value)
    if (parsed.scheme != 'https' or not parsed.hostname or not parsed.hostname.endswith(suffix)
            or parsed.hostname == suffix.lstrip('.') or parsed.username or parsed.password
            or parsed.port not in (None, 443) or parsed.query or parsed.fragment or parsed.path not in ('', '/')):
        raise AzureServiceError('Use the documented Azure HTTPS resource endpoint without a path, query or credential')
    return value.rstrip('/')


def enabled(name):
    return os.environ.get('PITCHPRISM_ENABLE_' + name) == '1'


def status():
    """Configuration only, never a claim of successful service operation."""
    return {name: {'enabled': active, 'verified': False} for name, active in [
        ('contentSafety', enabled('CONTENT_SAFETY')),
        ('blobReceipts', enabled('BLOB_RECEIPTS')),
        ('applicationInsights', enabled('TELEMETRY')),
        ('keyVault', bool(os.environ.get('AZURE_OPENAI_API_KEY_SECRET'))),
    ]}


def bearer(scope):
    try:
        from azure.identity import DefaultAzureCredential
        token = DefaultAzureCredential(exclude_interactive_browser_credential=True).get_token(scope)
        return {'Authorization': 'Bearer ' + token.token}
    except Exception as error:
        raise AzureServiceError('Azure managed identity or local CLI authentication is unavailable') from error


def request(url, *, method, headers, body=None):
    raw = json.dumps(body, allow_nan=False).encode() if body is not None else None
    req = urllib.request.Request(url, data=raw, method=method,
        headers={'Content-Type': 'application/json', **headers})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            result = response.read(1_048_577)
            if len(result) > 1_048_576:
                raise AzureServiceError('Azure service response exceeded the size limit')
            return json.loads(result) if result else {}
    except urllib.error.HTTPError as error:
        raise AzureServiceError(f'Azure service HTTP {error.code}; check identity, quota and configuration') from error
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise AzureServiceError('Azure service unavailable or returned an invalid response') from error


def load_key_vault_secret():
    """Optionally resolve one named Foundry key at server startup, never from user input."""
    name = os.environ.get('AZURE_OPENAI_API_KEY_SECRET', '')
    if not name:
        return
    if not re.fullmatch(r'[A-Za-z0-9-]{1,127}', name):
        raise AzureServiceError('Invalid Key Vault secret name')
    base = endpoint(os.environ.get('AZURE_KEY_VAULT_ENDPOINT', ''), '.vault.azure.net')
    result = request(base + '/secrets/' + name + '?api-version=7.4', method='GET',
        headers=bearer('https://vault.azure.net/.default'))
    if not isinstance(result.get('value'), str) or not result['value']:
        raise AzureServiceError('Key Vault did not return the configured secret')
    os.environ['AZURE_OPENAI_API_KEY'] = result['value']


def moderate_story(result):
    """Fail closed when explicitly enabled, including on unavailable or incomplete analysis."""
    if not enabled('CONTENT_SAFETY'):
        return {'status': 'disabled'}
    base = endpoint(os.environ.get('AZURE_CONTENT_SAFETY_ENDPOINT', ''), '.cognitiveservices.azure.com')
    key = os.environ.get('AZURE_CONTENT_SAFETY_KEY')
    headers = {'Ocp-Apim-Subscription-Key': key} if key else bearer('https://cognitiveservices.azure.com/.default')
    response = request(base + '/contentsafety/text:analyze?api-version=2024-09-01', method='POST', headers=headers,
        body={'text': result['headline'] + '\n' + result['explanation'],
              'categories': ['Hate', 'SelfHarm', 'Sexual', 'Violence'], 'outputType': 'EightSeverityLevels'})
    analyses = response.get('categoriesAnalysis', [])
    categories = {item.get('category'): item.get('severity') for item in analyses if isinstance(item, dict)}
    if set(categories) != {'Hate', 'SelfHarm', 'Sexual', 'Violence'} or any(
            type(value) is not int or not 0 <= value <= 7 for value in categories.values()):
        raise AzureServiceError('Content Safety returned incomplete category analysis')
    if any(value >= 4 for value in categories.values()):
        raise AzureServiceError('The generated explanation did not pass Content Safety')
    return {'status': 'passed', 'categories': categories}


def receipt(result):
    """Minimized operational receipt: no footage, prompts, prose or cloud request IDs."""
    return {'schemaVersion': 1, 'timestamp': datetime.now(timezone.utc).isoformat(),
        'provider': result['provider'], 'sourceSecond': result['sourceSecond'],
        'mode': result['mode'], 'tokens': result.get('tokens', 0),
        'evidenceIds': list(result['evidenceIds']),
        'tools': [{'tool': step.get('tool'), 'ok': bool(step.get('ok'))} for step in result.get('trace', [])]}


def store_receipt(data):
    if not enabled('BLOB_RECEIPTS'):
        return {'status': 'disabled'}
    base = endpoint(os.environ.get('AZURE_STORAGE_BLOB_ENDPOINT', ''), '.blob.core.windows.net')
    container = os.environ.get('AZURE_STORAGE_RECEIPT_CONTAINER', 'receipts')
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])', container) or '--' in container:
        raise AzureServiceError('Invalid private receipt container name')
    name = str(uuid.uuid4()) + '.json'
    request(base + '/' + container + '/' + name, method='PUT',
        headers={**bearer('https://storage.azure.com/.default'), 'x-ms-version': '2023-11-03',
                 'x-ms-blob-type': 'BlockBlob', 'x-ms-date': datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT'),
                 'If-None-Match': '*'}, body=data)
    return {'status': 'stored'}


def emit_metrics(data):
    if not enabled('TELEMETRY'):
        return {'status': 'disabled'}
    parts = dict(part.split('=', 1) for part in os.environ.get('APPLICATIONINSIGHTS_CONNECTION_STRING', '').split(';') if '=' in part)
    try:
        key = str(uuid.UUID(parts['InstrumentationKey']))
    except (KeyError, ValueError) as error:
        raise AzureServiceError('Invalid Application Insights configuration') from error
    base = endpoint(parts.get('IngestionEndpoint', ''), '.in.applicationinsights.azure.com')
    events = [{'name': 'Microsoft.ApplicationInsights.Metric', 'time': data['timestamp'], 'iKey': key,
        'data': {'baseType': 'MetricData', 'baseData': {'ver': 2,
            'metrics': [{'name': 'pitchprism.validated_explanations', 'value': 1, 'count': 1}],
            'properties': {'provider': data['provider'], 'audience': data['mode']}}}}]
    response = request(base + '/v2/track', method='POST', headers={}, body=events)
    if response.get('itemsAccepted') != 1:
        raise AzureServiceError('Application Insights did not accept the metric')
    return {'status': 'sent'}


def enrich_cloud_result(result):
    if result.get('provider') != 'azure-foundry':
        return result
    safety = moderate_story(result)
    data, services = receipt(result), {'contentSafety': safety}
    # Optional operational side effects must not turn a valid answer into an outage.
    for name, operation in [('blobReceipts', store_receipt), ('applicationInsights', emit_metrics)]:
        try:
            services[name] = operation(data)
        except AzureServiceError:
            services[name] = {'status': 'unavailable'}
    return {**result, 'azureServices': services}
