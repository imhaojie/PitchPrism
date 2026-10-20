import copy
import json
import math
import os
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

from product.football.analytics import available_angles, local_story, pass_distance, snapshot, validate_match
from product.football.data.generate import build_match
from product.football.foundry import FoundryError, run_agent, settings, validate_story
from product.football.server import Handler, ThreadingHTTPServer, validate_options

MATCH = build_match()


class FootballFacts(unittest.TestCase):
    def test_generated_fixture_matches_source(self):
        source = Path(__file__).resolve().parents[1] / 'data/match.json'
        self.assertEqual(json.loads(source.read_text()), MATCH)

    def test_dataset_is_explicitly_synthetic(self):
        self.assertTrue(validate_match(MATCH)['synthetic'])
        self.assertEqual(len(MATCH['roster']), 22)

    def test_zero_events_is_not_zero_accuracy(self):
        state = snapshot(MATCH, 0)
        self.assertIsNone(state['stats']['NBR']['passAccuracy'])
        self.assertIsNone(state['stats']['NBR']['xg'])
        self.assertEqual(state['events'], [])

    def test_future_goal_does_not_leak(self):
        state = snapshot(MATCH, 44.99)
        self.assertEqual(state['stats']['NBR']['goals'], 0)
        self.assertEqual(state['stats']['NBR']['xg'], .18)
        self.assertNotIn('evt-019', [e['id'] for e in state['events']])

    def test_goal_at_exact_boundary(self):
        state = snapshot(MATCH, 45)
        self.assertEqual(state['stats']['NBR']['goals'], 1)
        self.assertEqual(state['stats']['NBR']['xg'], .6)
        self.assertEqual(state['stats']['NBR']['shots'], 2)

    def test_accuracy_includes_failed_pass(self):
        state = snapshot(MATCH, 48)
        self.assertEqual(state['stats']['RIV']['passes'], 2)
        self.assertEqual(state['stats']['RIV']['completedPasses'], 1)
        self.assertEqual(state['stats']['RIV']['passAccuracy'], 50)
        self.assertEqual(state['stats']['NBR']['completedPasses'], 9)

    def test_distance_converts_normalized_axes_independently(self):
        event = next(e for e in MATCH['events'] if e['id'] == 'evt-008')
        self.assertAlmostEqual(pass_distance(event, MATCH), math.hypot(16.8, 31.28))
        self.assertEqual(snapshot(MATCH, 20)['facts'][0]['value'], 35.5)

    def test_missing_xg_is_not_silently_zero(self):
        match = copy.deepcopy(MATCH)
        del match['events'][-1]['xg']
        self.assertIsNone(snapshot(match, 48)['stats']['NBR']['xg'])

    def test_rewind_restores_earlier_state(self):
        snapshot(MATCH, 48)
        self.assertEqual(snapshot(MATCH, 20)['stats']['NBR']['goals'], 0)
        self.assertEqual(len(snapshot(MATCH, 20)['events']), 8)

    def test_invalid_times_are_rejected(self):
        for value in [float('nan'), float('inf'), True, '20']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                snapshot(MATCH, value)

    def test_time_clamps_to_excerpt(self):
        self.assertEqual(snapshot(MATCH, -2)['sourceSecond'], 0)
        self.assertEqual(snapshot(MATCH, 500)['sourceSecond'], 48)

    def test_event_identity_and_coordinates_validate(self):
        for key, value in [('playerId', 'unknown'), ('start', [101, 20]), ('xg', 1.1)]:
            match = copy.deepcopy(MATCH)
            match['events'][-1][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_match(match)

    def test_duplicate_or_unordered_events_rejected(self):
        for mutate in [lambda m: m['events'].append(m['events'][0]), lambda m: m['events'].reverse()]:
            match = copy.deepcopy(MATCH)
            mutate(match)
            with self.assertRaises(ValueError):
                validate_match(match)

    def test_personalization_changes_prose_and_references(self):
        state = snapshot(MATCH, 20)
        casual, analyst = local_story(state), local_story(state, 'analyst')
        self.assertNotEqual(casual['explanation'], analyst['explanation'])
        player = local_story(state, player='NBR-10')
        self.assertEqual(player['evidenceIds'], ['evt-008'])
        self.assertNotEqual(player['headline'], casual['headline'])

    def test_unseen_selection_has_no_invented_events(self):
        result = local_story(snapshot(MATCH, 20), player='RIV-1')
        self.assertEqual(result['evidenceIds'], [])
        self.assertIn('no events', result['explanation'])

    def test_unknown_preferences_rejected(self):
        for body in [{'mode':'expert'}, {'team':'NBA'}, {'player':'Messi'}]:
            with self.assertRaises(ValueError):
                validate_options(body)


def call(identifier, name, arguments):
    return {'id': identifier, 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(arguments)}}


def response(*calls):
    return {'choices':[{'message':{'role':'assistant','tool_calls':list(calls)}}], 'usage':{'total_tokens':100}}, 'test-request-id'


class FoundryContract(unittest.TestCase):
    def setUp(self):
        self.state = snapshot(MATCH, 20)
        self.candidate = {'headline':'The attack changes sides.', 'explanation':'Follow the receiving player after the completed diagonal pass.',
                          'angle':'switch', 'evidenceIds':['evt-008']}

    def test_requires_read_and_inspect_before_submission(self):
        for inspected, read in [(set(), True), ({'evt-008'},False)]:
            with self.assertRaises(ValueError):
                validate_story(self.candidate, self.state, inspected, read)

    def test_rejects_future_or_fabricated_evidence(self):
        for identifier in ['evt-019', 'fake']:
            value = {**self.candidate,'evidenceIds':[identifier]}
            with self.assertRaises(ValueError):
                validate_story(value,self.state,{identifier},True)

    def test_forbids_model_authored_numbers_and_causality(self):
        for prose in ['Pass accuracy was 100%.', 'Two defenders were forced to move.', 'This caused the goal.']:
            with self.subTest(prose=prose), self.assertRaises(ValueError):
                validate_story({**self.candidate,'explanation':prose},self.state,{'evt-008'},True)

    def test_requires_all_angle_evidence(self):
        with self.assertRaises(ValueError):
            validate_story({**self.candidate,'evidenceIds':['evt-007']},self.state,{'evt-007'},True)

    def test_bounded_tool_loop_returns_trace_after_validation(self):
        replies = iter([response(call('a','read_match_state',{})),response(call('b','read_evidence',{'evidenceIds':['evt-008']})),response(call('c','validate_story',self.candidate))])
        result = run_agent(self.state,transport=lambda *_:next(replies))
        self.assertEqual(result['provider'],'azure-foundry')
        self.assertEqual([t['tool'] for t in result['trace']],['read_match_state','read_evidence','validate_story'])
        self.assertEqual(result['tokens'],300)

    def test_invalid_submission_can_be_repaired(self):
        replies=iter([response(call('a','validate_story',self.candidate)),response(call('b','read_match_state',{})),response(call('c','read_evidence',{'evidenceIds':['evt-008']})),response(call('d','validate_story',self.candidate))])
        result=run_agent(self.state,transport=lambda *_:next(replies))
        self.assertFalse(result['trace'][0]['ok'])
        self.assertTrue(result['trace'][-1]['ok'])

    def test_repeated_tool_call_is_rejected(self):
        with self.assertRaises(FoundryError):
            run_agent(self.state,transport=lambda *_:response(call('same','read_match_state',{})))

    def test_round_budget_fails_closed(self):
        count=iter(range(99))
        with self.assertRaises(FoundryError):
            run_agent(self.state,transport=lambda *_:response(call(str(next(count)),'read_match_state',{})))

    def test_non_azure_endpoint_is_rejected(self):
        with patch.dict(os.environ, {'AZURE_OPENAI_ENDPOINT':'https://example.com/leak'}), self.assertRaises(FoundryError):
            settings()


class HttpDemo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()

    def get(self,path):
        return urllib.request.urlopen(self.base+path,timeout=4)

    def test_health_and_match_are_accessible(self):
        with self.get('/api/health') as response:
            self.assertEqual(json.load(response)['service'],'PitchPrism')
        with self.get('/api/match') as response:
            self.assertTrue(json.load(response)['synthetic'])

    def test_html_and_shared_player_are_served(self):
        for path,part in [('/',b'PitchPrism'),('/shared/media/player-controls.js',b'createPlayerControls')]:
            with self.get(path) as response:
                self.assertIn(part,response.read())
                self.assertIn("default-src 'self'",response.headers['Content-Security-Policy'])

    def test_secrets_and_historical_deployments_are_inaccessible(self):
        for path in ['/.env','/product/deployment.json','/media/../../.env','/shared/media/../app.js']:
            with self.subTest(path=path),self.assertRaises(urllib.error.HTTPError) as caught:
                self.get(path)
            self.assertEqual(caught.exception.code,404)

    def test_browser_cross_origin_explain_rejected(self):
        request=urllib.request.Request(self.base+'/api/explain',data=b'{"second":20}',headers={'Origin':'https://evil.example','Content-Type':'application/json'})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request)
        self.assertEqual(caught.exception.code,403)

    def test_local_explanation_is_not_claimed_as_cloud(self):
        request=urllib.request.Request(self.base+'/api/explain',data=b'{"second":20,"mode":"analyst"}',headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request) as response:
            result=json.load(response)
        self.assertEqual(result['provider'],'local')
        self.assertNotIn('trace',result)

    def test_invalid_time_returns_400(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.get('/api/snapshot?t=nan')
        self.assertEqual(caught.exception.code,400)

    def test_range_requests_support_video_seeking(self):
        # The static poster is always tracked; ranges share the exact media path implementation.
        request=urllib.request.Request(self.base+'/poster.jpg',headers={'Range':'bytes=2-11'})
        with urllib.request.urlopen(request) as response:
            self.assertEqual(response.status,206)
            self.assertEqual(len(response.read()),10)
            self.assertTrue(response.headers['Content-Range'].startswith('bytes 2-11/'))


if __name__=='__main__':
    unittest.main()
