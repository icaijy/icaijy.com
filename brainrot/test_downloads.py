import io
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .models import HallOfFameEntry


class HallOfFameMp4DownloadTests(TestCase):
    def setUp(self):
        self.private_directory = tempfile.TemporaryDirectory()
        self.override = override_settings(PRIVATE_MEDIA_ROOT=self.private_directory.name)
        self.override.enable()
        self.entry = HallOfFameEntry.objects.create(
            display_name='Phone Test',
            score=67,
            video=SimpleUploadedFile('phone.webm', b'legacy-test-bytes', content_type='video/webm'),
            mime_type='video/webm',
            duration_seconds=23,
            visibility=HallOfFameEntry.Visibility.PUBLIC,
        )
        self.path = f'/67/hall-of-fame/{self.entry.id}/video/'

    def tearDown(self):
        self.override.disable()
        self.private_directory.cleanup()

    def test_legacy_download_url_still_streams_original_file(self):
        response = self.client.get(f'{self.path}?download=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'video/webm')
        self.assertIn('.webm"', response['Content-Disposition'])

    @patch('brainrot.download_views.open_compatible_mp4')
    def test_explicit_mp4_download_returns_real_mp4_headers(self, transcode):
        transcode.return_value = (io.BytesIO(b'fake-mp4-for-response-test'), 26)
        response = self.client.get(f'{self.path}?download=1&format=mp4')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'video/mp4')
        self.assertEqual(response['Content-Length'], '26')
        self.assertIn('.mp4"', response['Content-Disposition'])
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        transcode.assert_called_once()

    def test_public_pages_point_download_buttons_at_mp4_format(self):
        leaderboard = self.client.get('/67/hall-of-fame/')
        self.assertContains(leaderboard, f'{self.path}?download=1&amp;format=mp4')
        self.assertContains(leaderboard, 'Download MP4')

        detail = self.client.get(f'/67/hall-of-fame/{self.entry.id}/')
        self.assertContains(detail, f'{self.path}?download=1&amp;format=mp4')
        self.assertContains(detail, 'Download MP4')
