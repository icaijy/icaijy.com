import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .models import HallOfFameEntry
from .validators import ValidatedVideo


class BrainrotPageTests(TestCase):
    def test_public_pages_load(self):
        for path in ('/67/', '/67/games/', '/67/hall-of-fame/', '/67/typing/'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)


@override_settings(TURNSTILE_ENABLED=False, HOF_SUBMISSIONS_PER_HOUR=1)
class HallOfFameSubmissionTests(TestCase):
    def setUp(self):
        self.private_directory = tempfile.TemporaryDirectory()
        self.override = override_settings(PRIVATE_MEDIA_ROOT=self.private_directory.name)
        self.override.enable()
        self.user = get_user_model().objects.create_user('scientist', password='test-password-67')

    def tearDown(self):
        self.override.disable()
        self.private_directory.cleanup()

    def test_anonymous_upload_is_rejected(self):
        response = self.client.post('/67/submit/', {'score': 67})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(HallOfFameEntry.objects.count(), 0)

    @patch('brainrot.views.validate_hall_of_fame_video')
    def test_valid_upload_is_pending_and_rate_limited(self, validate):
        validate.return_value = ValidatedVideo('video/webm', 'webm', 23.0)
        self.client.login(username='scientist', password='test-password-67')
        video = SimpleUploadedFile('run.webm', b'video evidence', content_type='video/webm')
        response = self.client.post('/67/submit/', {'score': 67, 'video': video})
        self.assertEqual(response.status_code, 201)
        entry = HallOfFameEntry.objects.get()
        self.assertEqual(entry.state, HallOfFameEntry.State.PENDING)
        self.assertFalse(self.client.get('/67/hall-of-fame/').context['entries'])

        second = SimpleUploadedFile('run.webm', b'more evidence', content_type='video/webm')
        response = self.client.post('/67/submit/', {'score': 68, 'video': second})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(HallOfFameEntry.objects.count(), 1)

    def test_pending_video_is_private_then_public_after_approval(self):
        entry = HallOfFameEntry.objects.create(
            user=self.user,
            score=61,
            video=SimpleUploadedFile('private.webm', b'private bytes', content_type='video/webm'),
            mime_type='video/webm',
            duration_seconds=20,
        )
        path = f'/67/hall-of-fame/{entry.id}/video/'
        self.assertEqual(self.client.get(path).status_code, 404)

        self.client.login(username='scientist', password='test-password-67')
        self.assertEqual(self.client.get(path).status_code, 200)
        self.client.logout()
        entry.state = HallOfFameEntry.State.APPROVED
        entry.save(update_fields=['state'])
        self.assertEqual(self.client.get(path).status_code, 200)
