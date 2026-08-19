import json
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .models import HallOfFameEntry
from .validators import ValidatedVideo, validate_hall_of_fame_video


@override_settings(DEBUG=True, TURNSTILE_ENABLED=False, HOF_SUBMISSIONS_PER_MINUTE=3)
class HallOfFameNativeVideoStorageTests(TestCase):
    def setUp(self):
        self.private_directory = tempfile.TemporaryDirectory()
        self.override = override_settings(PRIVATE_MEDIA_ROOT=self.private_directory.name)
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        self.private_directory.cleanup()

    @patch('brainrot.validators._probe_video', return_value=23.0)
    def test_validator_keeps_webm_upload_native(self, probe):
        payload = b'\x1aE\xdf\xa3browser-evidence'
        source = SimpleUploadedFile(
            'browser.webm',
            payload,
            content_type='video/webm',
        )

        inspected = validate_hall_of_fame_video(source)

        self.assertEqual(inspected, ValidatedVideo('video/webm', 'webm', 23.0))
        self.assertEqual(source.content_type, 'video/webm')
        self.assertEqual(source.name, 'browser.webm')
        self.assertEqual(source.read(), payload)

    @patch('brainrot.validators._probe_video', return_value=23.0)
    def test_validator_keeps_mp4_upload_native(self, probe):
        payload = b'\x00\x00\x00\x18ftypisom-browser-evidence'
        source = SimpleUploadedFile(
            'browser.mp4',
            payload,
            content_type='video/mp4',
        )

        inspected = validate_hall_of_fame_video(source)

        self.assertEqual(inspected, ValidatedVideo('video/mp4', 'mp4', 23.0))
        self.assertEqual(source.content_type, 'video/mp4')
        self.assertEqual(source.name, 'browser.mp4')
        self.assertEqual(source.read(), payload)

    @patch('brainrot.video_mp4.transcode_upload_to_content_file')
    @patch('brainrot.validators._probe_video', return_value=23.0)
    def test_submission_persists_native_webm_without_server_transcode(self, probe, transcode):
        payload = b'\x1aE\xdf\xa3browser-evidence'
        source = SimpleUploadedFile(
            'browser.webm',
            payload,
            content_type='video/webm',
        )

        response = self.client.post('/67/submit/', {
            'score': 3,
            'display_name': 'Native Swan',
            'event_timeline': json.dumps([1.0, 2.0, 3.0]),
            'publication_consent': 'yes',
            'video': source,
        })

        self.assertEqual(response.status_code, 201)
        transcode.assert_not_called()
        entry = HallOfFameEntry.objects.get()
        self.assertEqual(entry.mime_type, 'video/webm')
        self.assertTrue(entry.video.name.endswith('.webm'))
        self.assertEqual(entry.video.read(), payload)

    @patch('brainrot.video_mp4.transcode_upload_to_content_file')
    @patch('brainrot.validators._probe_video', return_value=23.0)
    def test_submission_persists_native_mp4_without_server_transcode(self, probe, transcode):
        payload = b'\x00\x00\x00\x18ftypisom-browser-evidence'
        source = SimpleUploadedFile(
            'browser.mp4',
            payload,
            content_type='video/mp4',
        )

        response = self.client.post('/67/submit/', {
            'score': 3,
            'display_name': 'MP4 Swan',
            'event_timeline': json.dumps([1.0, 2.0, 3.0]),
            'publication_consent': 'yes',
            'video': source,
        })

        self.assertEqual(response.status_code, 201)
        transcode.assert_not_called()
        entry = HallOfFameEntry.objects.get()
        self.assertEqual(entry.mime_type, 'video/mp4')
        self.assertTrue(entry.video.name.endswith('.mp4'))
        self.assertEqual(entry.video.read(), payload)
