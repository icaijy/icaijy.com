import json
import tempfile
from contextlib import contextmanager
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .models import HallOfFameEntry, HallOfFameUploadAttempt
from .validators import ValidatedVideo
from .video_mp4 import Mp4TranscodeError


@override_settings(DEBUG=True, TURNSTILE_ENABLED=False, HOF_SUBMISSIONS_PER_MINUTE=3)
class HallOfFameCanonicalMp4StorageTests(TestCase):
    def setUp(self):
        self.private_directory = tempfile.TemporaryDirectory()
        self.override = override_settings(PRIVATE_MEDIA_ROOT=self.private_directory.name)
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        self.private_directory.cleanup()

    @staticmethod
    @contextmanager
    def fake_mp4(_upload):
        yield SimpleUploadedFile(
            'canonical.mp4',
            b'canonical-mp4-bytes',
            content_type='video/mp4',
        )

    @patch('brainrot.views.validate_hall_of_fame_video')
    @patch('brainrot.upload_views.transcode_upload_to_mp4')
    def test_new_submission_persists_only_mp4(self, transcode, validate):
        validate.return_value = ValidatedVideo('video/webm', 'webm', 23.0)
        transcode.side_effect = self.fake_mp4
        source = SimpleUploadedFile(
            'browser.webm',
            b'\x1aE\xdf\xa3browser-evidence',
            content_type='video/webm',
        )

        response = self.client.post('/67/submit/', {
            'score': 3,
            'display_name': 'MP4 Swan',
            'event_timeline': json.dumps([1.0, 2.0, 3.0]),
            'publication_consent': 'yes',
            'video': source,
        })

        self.assertEqual(response.status_code, 201)
        entry = HallOfFameEntry.objects.get()
        self.assertEqual(entry.mime_type, 'video/mp4')
        self.assertTrue(entry.video.name.endswith('.mp4'))
        self.assertEqual(entry.video.read(), b'canonical-mp4-bytes')
        transcode.assert_called_once()

    @patch('brainrot.views.validate_hall_of_fame_video')
    @patch('brainrot.upload_views.transcode_upload_to_mp4')
    def test_transcode_failure_does_not_publish_entry(self, transcode, validate):
        validate.return_value = ValidatedVideo('video/webm', 'webm', 23.0)
        transcode.side_effect = Mp4TranscodeError('ffmpeg failed')
        source = SimpleUploadedFile(
            'browser.webm',
            b'\x1aE\xdf\xa3browser-evidence',
            content_type='video/webm',
        )

        response = self.client.post('/67/submit/', {
            'score': 1,
            'display_name': 'Failed Swan',
            'event_timeline': '[1.0]',
            'publication_consent': 'yes',
            'video': source,
        })

        self.assertEqual(response.status_code, 503)
        self.assertEqual(HallOfFameEntry.objects.count(), 0)
        attempt = HallOfFameUploadAttempt.objects.get()
        self.assertFalse(attempt.accepted)
