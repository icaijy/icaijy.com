import tempfile

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
            video=SimpleUploadedFile('phone.mp4', b'already-canonical-mp4', content_type='video/mp4'),
            mime_type='video/mp4',
            duration_seconds=23,
            visibility=HallOfFameEntry.Visibility.PUBLIC,
        )
        self.path = f'/67/hall-of-fame/{self.entry.id}/video/'

    def tearDown(self):
        self.override.disable()
        self.private_directory.cleanup()

    def test_download_streams_stored_mp4_directly(self):
        response = self.client.get(f'{self.path}?download=1&format=mp4')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'video/mp4')
        self.assertEqual(response['Content-Length'], str(self.entry.video.size))
        self.assertIn('.mp4"', response['Content-Disposition'])
        self.assertEqual(response['Cache-Control'], 'private, max-age=300')

    def test_inline_playback_uses_same_stored_file(self):
        response = self.client.get(self.path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'video/mp4')
        self.assertTrue(response['Content-Disposition'].startswith('inline;'))

    def test_migration_window_does_not_lie_about_legacy_extension(self):
        legacy = HallOfFameEntry.objects.create(
            display_name='Legacy Test',
            score=61,
            video=SimpleUploadedFile('legacy.webm', b'legacy-bytes', content_type='video/webm'),
            mime_type='video/webm',
            duration_seconds=23,
            visibility=HallOfFameEntry.Visibility.PUBLIC,
        )
        response = self.client.get(f'/67/hall-of-fame/{legacy.id}/video/?download=1&format=mp4')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'video/webm')
        self.assertIn('.webm"', response['Content-Disposition'])

    def test_public_pages_keep_download_buttons_on_video_endpoint(self):
        leaderboard = self.client.get('/67/hall-of-fame/')
        self.assertContains(leaderboard, f'{self.path}?download=1&amp;format=mp4')
        self.assertContains(leaderboard, 'Download MP4')

        detail = self.client.get(f'/67/hall-of-fame/{self.entry.id}/')
        self.assertContains(detail, f'{self.path}?download=1&amp;format=mp4')
        self.assertContains(detail, 'Download MP4')
