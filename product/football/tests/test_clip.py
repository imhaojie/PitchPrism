"""Real excerpt provenance, timeline, time bounds and shared Agent context."""
import json
import unittest
from unittest.mock import patch
from product.football import clip
from product.football.foundry import run_agent, validate_story
from product.football.scripts import verify_foundry
from infra.azure.deploy import require_free_subscription
from product.football.tests import test_football as http_helpers
call, response = http_helpers.call, http_helpers.response


class ReviewedClip(unittest.TestCase):
    def test_source_is_separate_from_synthetic_events(self):
        state=clip.snapshot(66.6)
        self.assertFalse(state['synthetic'])
        self.assertEqual(state['stats']['scoreboard'],{'MCI':0,'NEW':0})
        self.assertIsNone(state['stats']['xg'])
        self.assertIsNone(state['stats']['passAccuracy'])
        self.assertNotIn('NBR',json.dumps(state))

    def test_no_future_observations_or_scene_on_rewind(self):
        clip.snapshot(66.6)
        self.assertIsNone(clip.snapshot(7.99)['scene'])
        self.assertEqual(clip.snapshot(37.8)['scene']['id'],'combine')
        self.assertNotIn('clip-release',[e['id'] for e in clip.snapshot(56.79)['events']])

    def test_entire_original_is_present_once_before_replay(self):
        live=[s for s in clip.CLIP['production']['timeline'] if s['kind']=='live']
        self.assertEqual(live[0]['sourceStart'],0)
        self.assertEqual(live[-1]['sourceEnd'],66.6)
        for a,b in zip(live,live[1:]):self.assertEqual(a['sourceEnd'],b['sourceStart'])
        self.assertAlmostEqual(sum(s['sourceEnd']-s['sourceStart'] for s in live),66.6)

    def test_contiguous_output_and_exact_frame_boundaries(self):
        timeline=clip.CLIP['production']['timeline']
        for a,b in zip(timeline,timeline[1:]):self.assertEqual(a['outputEnd'],b['outputStart'])
        for s in timeline:
            for k in ['outputStart','outputEnd','sourceStart','sourceEnd']:self.assertAlmostEqual(s[k]*25,round(s[k]*25))
        self.assertEqual(timeline[-1]['outputEnd'],118.4)
        self.assertLess(timeline[-1]['outputEnd'],120)

    def test_freezes_are_exact_reviewed_frames(self):
        scenes={s['id']:s for s in clip.CLIP['scenes']}
        for s in clip.CLIP['production']['timeline']:
            if s['kind']=='freeze':
                self.assertEqual(s['sourceStart'],scenes[s['scene']]['second'])
                self.assertEqual(s['sourceEnd'],s['sourceStart'])
                for p in scenes[s['scene']]['players']:
                    self.assertTrue(0<=p['foot'][0]<1280 and 0<=p['foot'][1]<720)
                    self.assertEqual(p['anchorKind'],'visible-foot')

    def test_invalid_times_fail_closed(self):
        for t in [-1,67,float('nan'),float('inf'),True,'8',None]:
            with self.subTest(t=t),self.assertRaises((ValueError,TypeError)):clip.snapshot(t)

    def test_preferences_change_explanation_without_changing_evidence(self):
        state=clip.snapshot(56.8)
        self.assertNotEqual(clip.local_story(state)['explanation'],clip.local_story(state,'analyst')['explanation'])
        self.assertNotEqual(clip.local_story(state)['explanation'],clip.local_story(state,player='right')['explanation'])
        self.assertEqual(clip.local_story(state,player='right')['evidenceIds'],['clip-release'])

    def test_same_foundry_loop_can_read_reviewed_clip_context(self):
        state=clip.snapshot(37.8);candidate=dict(headline='Follow the ball inside',explanation='Look towards the runner near the box and check the defenders ahead.',angle='clip-combine',evidenceIds=['clip-combine'])
        replies=iter([response(call('a','read_match_state',{})),response(call('b','read_evidence',{'evidenceIds':['clip-combine']})),response(call('c','validate_story',candidate))])
        prompts=[]
        def transport(messages,*_):prompts.append(messages[0]['content']);return next(replies)
        result=run_agent(state,transport=transport,context=clip.AGENT_CONTEXT)
        self.assertEqual(len(result['trace']),3)
        self.assertIn('real user-provided',prompts[0])
        self.assertNotIn('ORIGINAL SYNTHETIC',prompts[0])
        with self.assertRaises(ValueError):validate_story({**candidate,'evidenceIds':['clip-release']},state,{'clip-release'},True,clip.angles)


class ClipHTTP(unittest.TestCase):
    setUpClass = classmethod(http_helpers.HttpDemo.setUpClass.__func__)
    tearDownClass = classmethod(http_helpers.HttpDemo.tearDownClass.__func__)
    get = http_helpers.HttpDemo.get
    def test_clip_endpoint_and_source_time_are_real(self):
        with self.get('/api/clip') as response:self.assertFalse(json.load(response)['synthetic'])
        with self.get('/api/clip/snapshot?t=8') as response:self.assertEqual(json.load(response)['scene']['id'],'build')

    def test_local_clip_explain_uses_no_synthetic_names(self):
        import urllib.request
        request=urllib.request.Request(self.base+'/api/clip/explain',data=b'{"second":56.8,"player":"right"}',headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request) as response:result=json.load(response)
        self.assertEqual(result['provider'],'local')
        self.assertEqual(result['evidenceIds'],['clip-release'])
        self.assertNotIn('NORTHBRIDGE',json.dumps(result))


class CloudReceiptContract(unittest.TestCase):
    """Fake responses test receipt validation only; they never certify cloud access."""
    def test_default_receipt_is_bound_to_the_active_real_clip(self):
        fake = {'provider':'azure-foundry', 'trace':[{'tool':name, 'ok':True} for name in
                ['read_match_state','read_evidence','validate_story']]}
        with patch.object(verify_foundry, 'settings', return_value={'configured':True}), patch.object(verify_foundry, 'run_agent', return_value=fake) as agent:
            receipt = verify_foundry.verify()
        self.assertFalse(receipt['synthetic'])
        self.assertEqual(receipt['scenario'],'clip')
        self.assertEqual(receipt['sourceSha256'],clip.CLIP['source']['sha256'])
        self.assertEqual(receipt['sourceSecond'],37.8)
        self.assertIs(agent.call_args.kwargs['context'],clip.AGENT_CONTEXT)

    def test_unconfigured_or_incomplete_calls_cannot_create_a_receipt(self):
        with patch.object(verify_foundry, 'settings', return_value={'configured':False}), patch.object(verify_foundry, 'run_agent') as agent:
            with self.assertRaises(RuntimeError):verify_foundry.verify()
            agent.assert_not_called()
        for result in [{'provider':'local','trace':[]},{'provider':'azure-foundry','trace':[{'tool':'validate_story','ok':True}]}]:
            with patch.object(verify_foundry, 'settings', return_value={'configured':True}), patch.object(verify_foundry, 'run_agent', return_value=result):
                with self.assertRaises(RuntimeError):verify_foundry.verify()

    def test_deployment_rejects_paid_or_unprotected_billing(self):
        for policy in [{'quotaId':'PayAsYouGo_2014-09-01','spendingLimit':'Off'},
                       {'quotaId':'AzureForStudents_2018-01-01','spendingLimit':'Off'}, {}]:
            with self.subTest(policy=policy),self.assertRaises(RuntimeError):
                require_free_subscription({'state':'Enabled','subscriptionPolicies':policy})
        require_free_subscription({'state':'Enabled','subscriptionPolicies':{
            'quotaId':'AzureForStudents_2018-01-01','spendingLimit':'On'}})
