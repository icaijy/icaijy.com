import json
import tempfile
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .models import HallOfFameEntry
from .validators import ValidatedVideo, validate_hall_of_fame_video
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

    @patch('brainrot.validators._probe_video', return_value=23.0)
    @patch('brainrot.validators.transcode_upload_to_content_file')
    def test_validator_replaces_browser_upload_with_mp4(self, transcode, probe):
        source = SimpleUploadedFile(
            'browser.webm',
            b'\x1aE\xdf\xa3browser-evidence',
            content_type='video/webm',
        )
        transcode.return_value = ContentFile(b'canonical-mp4-bytes', name='recording.mp4')

        inspected = validate_hall_of_fame_video(source)

        self.assertEqual(inspected, ValidatedVideo('video/mp4', 'mp4', 23.0))
        self.assertEqual(source.content_type, 'video/mp4')
        self.assertTrue(source.name.endswith('.mp4'))
        self.assertEqual(source.read(), b'canonical-mp4-bytes')

    @patch('brainrot.views.validate_hall_of_fame_video')
    def test_submission_persists_canonicalised_upload(self, validate):
        def canonicalise(upload):
            canonical = ContentFile(b'canonical-mp4-bytes', name='recording.mp4')
            upload.file = canonical
            upload.name = canonical.name
            upload.size = canonical.size
            upload.content_type = 'video/mp4'
            return ValidatedVideo('video/mp4', 'mp4', 23.0)

        validate.side_effect = canonicalise
        source = SimpleUploadedFile('browser.webm', b'placeholder', content_type='video/webm')
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

    @patch('brainrot.validators._probe_video', return_value=23.0)
    @patch('brainrot.validators.transcode_upload_to_content_file')
    def test_transcode_failure_is_validation_failure(self, transcode, probe):
        transcode.side_effect = Mp4TranscodeError('ffmpeg failed')
        source = SimpleUploadedFile(
            'browser.webm',
            b'\x1aE\xdf\xa3browser-evidence',
            content_type='video/webm',
        )
        with self.assertRaisesMessage(ValidationError, 'ffmpeg failed'):
            validate_hall_of_fame_video(source)
        self.assertEqual(HallOfFameEntry.objects.count(), 0)
