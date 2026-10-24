"""Release regressions: stale timing and mismatched bytes must not reach the demo."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from product.football.clip import CLIP
from product.football.scripts.media_release import digest, verify_manifest, verify_release


class MediaRelease(unittest.TestCase):
    def fixture(self, base):
        build, data = base / 'build', base / 'data'
        build.mkdir(); data.mkdir()
        (data / 'clip.json').write_text(json.dumps(CLIP))
        (build / 'source.mp4').write_bytes(b'source fixture; not real media')
        (build / 'enhanced.mp4').write_bytes(b'enhanced fixture; not real media')
        manifest = dict(source=CLIP['source'], dataSha256=digest(data / 'clip.json'),
            timeline=CLIP['production']['timeline'], durationSeconds=118.4,
            outputSha256=digest(build / 'enhanced.mp4'))
        (build / 'manifest.json').write_text(json.dumps(manifest))
        lock = {name: digest(build / name) for name in ['manifest.json', 'source.mp4', 'enhanced.mp4']}
        (data / 'media-lock.json').write_text(json.dumps(lock))
        return build, data, manifest, lock

    def test_release_identity_and_timeline_are_checked_together(self):
        with tempfile.TemporaryDirectory() as temporary:
            build, data, manifest, lock = self.fixture(Path(temporary))
            self.assertEqual(verify_release(build, data), manifest)
            for field, value in [('durationSeconds', 97.2), ('timeline', []),
                                 ('dataSha256', '0' * 64), ('outputSha256', '0' * 64),
                                 ('source', {'sha256': '0' * 64})]:
                changed = deepcopy(manifest); changed[field] = value
                with self.subTest(field=field), self.assertRaises(ValueError):
                    verify_manifest(changed, CLIP, digest(data / 'clip.json'), lock)

    def test_changed_video_bytes_and_unlisted_assets_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            build, data, _, lock = self.fixture(Path(temporary))
            (build / 'enhanced.mp4').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                verify_release(build, data)
            lock['private-receipt.json'] = '0' * 64
            (data / 'media-lock.json').write_text(json.dumps(lock))
            with self.assertRaisesRegex(ValueError, 'exactly'):
                verify_release(build, data)
