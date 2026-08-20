import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .admin import HallOfFameEntryAdminForm
from .models import HallOfFameEntry
from .validators import ValidatedVideo


class ManualHallOfFameAdminUploadTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='manual67', password='x')

    def test_admin_upload_populates_video_metadata_and_allows_empty_timeline(self):
        with tempfile.TemporaryDirectory() as media_root, override_settings(PRIVATE_MEDIA_ROOT=media_root):
            upload = SimpleUploadedFile(
                'restored.webm',
                b'fake-video-for-mocked-validator',
                content_type='video/webm',
            )
            with patch(
                'brainrot.admin.validate_hall_of_fame_video',
                return_value=ValidatedVideo('video/webm', 'webm', 20.25),
            ):
                form = HallOfFameEntryAdminForm(
                    data={
                        'user': self.user.pk,
                        'display_name': '',
                        'game_mode': HallOfFameEntry.GameMode.SIX_SEVEN,
                        'score': 167,
                        'visibility': HallOfFameEntry.Visibility.PUBLIC,
                    },
                    files={'video': upload},
                )
                self.assertTrue(form.is_valid(), form.errors.as_json())
                entry = form.save()

            entry.refresh_from_db()
            self.assertEqual(entry.user, self.user)
            self.assertEqual(entry.mime_type, 'video/webm')
            self.assertAlmostEqual(entry.duration_seconds, 20.25)
            self.assertEqual(entry.event_timeline, [])
            self.assertEqual(entry.metrics, {})
            self.assertTrue(entry.video.name.endswith('.webm'))

    def test_admin_video_validation_error_stays_on_form_instead_of_500(self):
        upload = SimpleUploadedFile('broken.mp4', b'nope', content_type='video/mp4')
        from django.core.exceptions import ValidationError

        with patch(
            'brainrot.admin.validate_hall_of_fame_video',
            side_effect=ValidationError('The uploaded file is not a readable video.'),
        ):
            form = HallOfFameEntryAdminForm(
                data={
                    'user': self.user.pk,
                    'display_name': '',
                    'game_mode': HallOfFameEntry.GameMode.SIX_SEVEN,
                    'score': 100,
                    'visibility': HallOfFameEntry.Visibility.PRIVATE,
                },
                files={'video': upload},
            )
            self.assertFalse(form.is_valid())
            self.assertIn('not a readable video', str(form.errors['video']))
