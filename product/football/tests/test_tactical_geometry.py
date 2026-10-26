"""The tactical graphics must agree with the ground plane measured from each still's pitch markings."""
import copy
import unittest

from product.football import tactical_geometry as tg


class TacticalGeometryTest(unittest.TestCase):
    def setUp(self):
        self.clip, self.story, self.geometry = tg.load()

    def test_every_drawn_layer_is_supported_by_the_measured_frame(self):
        measured = tg.validate(self.clip, self.story, self.geometry)
        for model in measured.values():
            self.assertLessEqual(model['error'], tg.TOLERANCE_METRES)

    def test_original_link_arrow_through_the_presser_is_rejected(self):
        story = copy.deepcopy(self.story)
        story['scenes']['build']['steps'][1].update(routes=[0], layers=[])
        with self.assertRaisesRegex(ValueError, 'covered by press'):
            tg.validate(self.clip, story, self.geometry)

    def test_zones_and_goal_side_claims_follow_measured_positions(self):
        ground = tg.validate(self.clip, self.story, self.geometry)
        scene = {s['id']: s for s in self.clip['scenes']}
        step = {'routes': [], 'layers': [{'type': 'space', 'around': 'right', 'radius': 5.6}]}
        with self.assertRaisesRegex(ValueError, 'space zone'):
            tg.check_step(scene['release'], step, ground['release']['ground'])
        step = {'routes': [], 'layers': [{'type': 'goal-side', 'ball': 'carrier', 'defenders': ['press']}]}
        with self.assertRaisesRegex(ValueError, 'not goal-side'):
            tg.check_step(scene['combine'], step, ground['combine']['ground'])

    def test_combine_runner_is_level_and_central_not_ahead(self):
        g = tg.validate(self.clip, self.story, self.geometry)['combine']['ground']
        self.assertLess(g['runner'][0], g['carrier'][0] + 1)
        self.assertGreater(g['runner'][1] - g['carrier'][1], 8)

    def test_bad_marking_is_refused(self):
        geometry = copy.deepcopy(self.geometry)
        geometry['scenes']['release']['markings'][1]['image'] = [1660, 283]
        with self.assertRaisesRegex(ValueError, 'misses its markings'):
            tg.measure(self.clip, geometry)


if __name__ == '__main__':
    unittest.main()
