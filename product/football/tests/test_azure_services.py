"""Offline adapter contracts. No test in this file calls Azure or certifies deployment."""
import json
import os
import unittest
from unittest.mock import patch

from product.football import azure_services as azure


RESULT = {'provider': 'azure-foundry', 'headline': 'Watch the inside option',
    'explanation': 'Compare the visible defender with the available passing option.',
    'sourceSecond': 20, 'mode': 'analyst', 'tokens': 900, 'evidenceIds': ['evt-008'],
    'trace': [{'tool': 'validate_story', 'ok': True, 'requestId': 'private-account-request'}]}


class AzureServices(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=True); self.env.start(); self.addCleanup(self.env.stop)

    def test_defaults_make_no_network_or_identity_calls(self):
        with patch.object(azure, 'request', side_effect=AssertionError('network')), patch.object(azure, 'bearer', side_effect=AssertionError('identity')):
            azure.load_key_vault_secret()
            result = azure.enrich_cloud_result(RESULT)
        self.assertEqual({value['status'] for value in result['azureServices'].values()}, {'disabled'})
        self.assertTrue(all(not value['enabled'] and not value['verified'] for value in azure.status().values()))

    def test_local_stories_never_reach_azure_adapters(self):
        with patch.object(azure, 'moderate_story', side_effect=AssertionError('cloud')):
            result = azure.enrich_cloud_result({**RESULT, 'provider': 'local'})
        self.assertNotIn('azureServices', result)

    def test_endpoints_reject_non_azure_and_credential_urls(self):
        for url in ['http://example.vault.azure.net', 'https://vault.azure.net', 'https://x.vault.azure.net.evil.test',
                    'https://x.vault.azure.net/secret', 'https://x.vault.azure.net?key=secret', 'https://user@x.vault.azure.net',
                    'https://x.vault.azure.net:8443']:
            with self.subTest(url=url), self.assertRaises(azure.AzureServiceError):
                azure.endpoint(url, '.vault.azure.net')

    def safety(self, response):
        os.environ.update(PITCHPRISM_ENABLE_CONTENT_SAFETY='1', AZURE_CONTENT_SAFETY_ENDPOINT='https://test.cognitiveservices.azure.com')
        with patch.object(azure, 'bearer', return_value={}), patch.object(azure, 'request', return_value=response) as request:
            result = azure.moderate_story(RESULT)
        return result, request

    def test_moderation_uses_only_generated_prose(self):
        response = {'categoriesAnalysis': [{'category': c, 'severity': 0} for c in ['Hate', 'SelfHarm', 'Sexual', 'Violence']]}
        result, request = self.safety(response)
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(request.call_args.kwargs['body']['text'], RESULT['headline'] + '\n' + RESULT['explanation'])
        self.assertNotIn('trace', request.call_args.kwargs['body'])

    def test_moderation_fails_closed_for_risk_or_incomplete_analysis(self):
        for response in [{}, {'categoriesAnalysis': []}, {'categoriesAnalysis': [{'category':c, 'severity':4} for c in ['Hate','SelfHarm','Sexual','Violence']]}]:
            with self.subTest(response=response), self.assertRaises(azure.AzureServiceError):
                self.safety(response)

    def test_enabled_safety_failure_cannot_be_returned_as_validated(self):
        with patch.object(azure, 'moderate_story', side_effect=azure.AzureServiceError('unavailable')):
            with self.assertRaises(azure.AzureServiceError): azure.enrich_cloud_result(RESULT)

    def test_receipts_exclude_prose_prompts_request_ids_and_credentials(self):
        result = azure.receipt({**RESULT, 'prompt': 'private prompt', 'api-key': 'private key'})
        serialized = json.dumps(result)
        for value in ['private', RESULT['headline'], RESULT['explanation']]: self.assertNotIn(value, serialized)
        self.assertEqual(result['evidenceIds'], ['evt-008'])

    def test_storage_uses_private_container_identity_and_unique_blob(self):
        os.environ.update(PITCHPRISM_ENABLE_BLOB_RECEIPTS='1', AZURE_STORAGE_BLOB_ENDPOINT='https://test.blob.core.windows.net/')
        with patch.object(azure, 'bearer', return_value={'Authorization':'Bearer test-only'}), patch.object(azure, 'request', return_value={}) as request:
            self.assertEqual(azure.store_receipt(azure.receipt(RESULT))['status'], 'stored')
        self.assertIn('/receipts/', request.call_args.args[0])
        self.assertEqual(request.call_args.kwargs['headers']['If-None-Match'], '*')

    def test_storage_rejects_path_injection(self):
        os.environ.update(PITCHPRISM_ENABLE_BLOB_RECEIPTS='1', AZURE_STORAGE_BLOB_ENDPOINT='https://test.blob.core.windows.net', AZURE_STORAGE_RECEIPT_CONTAINER='../public')
        with self.assertRaises(azure.AzureServiceError): azure.store_receipt(azure.receipt(RESULT))

    def test_optional_operational_outages_do_not_hide_validated_answer(self):
        with patch.object(azure, 'store_receipt', side_effect=azure.AzureServiceError('storage')), patch.object(azure, 'emit_metrics', side_effect=azure.AzureServiceError('monitor')):
            result = azure.enrich_cloud_result(RESULT)
        self.assertEqual(result['headline'], RESULT['headline'])
        self.assertEqual(result['azureServices']['blobReceipts']['status'], 'unavailable')

    def test_key_vault_resolves_only_explicit_server_secret(self):
        os.environ.update(AZURE_KEY_VAULT_ENDPOINT='https://test.vault.azure.net', AZURE_OPENAI_API_KEY_SECRET='foundry-key')
        with patch.object(azure, 'bearer', return_value={}), patch.object(azure, 'request', return_value={'value':'test-only-value'}) as request:
            azure.load_key_vault_secret()
        self.assertEqual(os.environ['AZURE_OPENAI_API_KEY'], 'test-only-value')
        self.assertIn('/secrets/foundry-key?', request.call_args.args[0])

    def test_key_vault_rejects_arbitrary_secret_paths(self):
        os.environ.update(AZURE_KEY_VAULT_ENDPOINT='https://test.vault.azure.net', AZURE_OPENAI_API_KEY_SECRET='../other')
        with self.assertRaises(azure.AzureServiceError): azure.load_key_vault_secret()

    def test_monitoring_sends_metric_without_prose_or_identity(self):
        os.environ.update(PITCHPRISM_ENABLE_TELEMETRY='1', APPLICATIONINSIGHTS_CONNECTION_STRING='InstrumentationKey=00000000-0000-0000-0000-000000000001;IngestionEndpoint=https://eastus-8.in.applicationinsights.azure.com/')
        with patch.object(azure, 'request', return_value={'itemsAccepted':1}) as request:
            self.assertEqual(azure.emit_metrics(azure.receipt(RESULT))['status'], 'sent')
        raw = json.dumps(request.call_args.kwargs['body'])
        self.assertNotIn(RESULT['headline'], raw); self.assertNotIn('evt-008', raw)

    def test_monitoring_rejects_invalid_connection_and_partial_acceptance(self):
        os.environ['PITCHPRISM_ENABLE_TELEMETRY'] = '1'
        with self.assertRaises(azure.AzureServiceError): azure.emit_metrics(azure.receipt(RESULT))
        os.environ['APPLICATIONINSIGHTS_CONNECTION_STRING'] = 'InstrumentationKey=00000000-0000-0000-0000-000000000001;IngestionEndpoint=https://eastus-8.in.applicationinsights.azure.com'
        with patch.object(azure, 'request', return_value={'itemsAccepted':0}), self.assertRaises(azure.AzureServiceError):
            azure.emit_metrics(azure.receipt(RESULT))


if __name__ == '__main__': unittest.main()
