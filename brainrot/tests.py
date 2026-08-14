import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .models import HallOfFameEntry
from .validators import ValidatedVideo, _packet_duration, _probe_video


class BrainrotPageTests(TestCase):
    def test_public_pages_load(self):
        for path in ('/67/', '/67/counter/', '/67/hall-of-fame/', '/67/typing/'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

        legacy = self.client.get('/67/games/')
        self.assertEqual(legacy.status_code, 301)
        self.assertEqual(legacy['Location'], '/67/')

    def test_counter_uses_cache_busted_runtime_and_has_share_box(self):
        response = self.client.get('/67/counter/')
        self.assertContains(response, 'brainrot.css?v=20260814.5')
        self.assertContains(response, 'counter.js?v=20260814.9')
        self.assertContains(response, 'id="counter-share-text"')
        self.assertContains(response, 'id="copy-counter-share"')
        self.assertContains(response, 'id="download-recording"')
        self.assertNotContains(response, 'Run classification')
        self.assertNotContains(response, 'Casual Run')
        self.assertContains(response, 'nothing uploads unless you press Submit to Hall of Fame')

        script_path = finders.find('brainrot/counter.js')
        self.assertIsNotNone(script_path)
        script = Path(script_path).read_text(encoding='utf-8')
        self.assertIn('@mediapipe/tasks-vision@1.0.1/vision_bundle.mjs', script)
        self.assertNotIn('@mediapipe/tasks-vision@0.10.26', script)
        self.assertIn("startButton.disabled = false;", script)
        self.assertIn("if (poseReady) {\n              beginRun();", script)
        self.assertIn("new URL('/67/counter/', window.location.origin)", script)
        self.assertIn('preloadPoseRuntime();', script)
        self.assertLess(script.index('preloadPoseRuntime();'), script.index("enableButton.addEventListener('click'"))
        self.assertIn('return [11, 12, 15, 16].every', script)
        self.assertNotIn('currentMode', script)
        self.assertNotIn('modeInputs', script)
        self.assertIn('const blob = await stopRecording();', script)


class VideoValidationTests(TestCase):
    @patch('brainrot.validators.subprocess.run')
    def test_packet_duration_uses_span_not_absolute_camera_timestamp(self, run):
        run.return_value = SimpleNamespace(
            returncode=0,
            stdout='87.000000,0.033333\n109.966667,0.033333\n',
        )
        self.assertAlmostEqual(_packet_duration('/tmp/run.webm', '/usr/bin/ffprobe'), 23.0)

    @patch('brainrot.validators.subprocess.run')
    def test_packet_duration_keeps_pts_when_packet_duration_is_na(self, run):
        run.return_value = SimpleNamespace(
            returncode=0,
            stdout='87.000000,N/A\n109.966667,N/A\n',
        )
        self.assertAlmostEqual(
            _packet_duration('/tmp/firefox-run.webm', '/usr/bin/ffprobe'),
            22.966667,
        )

    @override_settings(HOF_MAX_VIDEO_SECONDS=26)
    @patch('brainrot.validators.shutil.which', return_value='/usr/bin/ffprobe')
    @patch('brainrot.validators._packet_duration', return_value=0)
    @patch('brainrot.validators.subprocess.run')
    def test_invalid_duration_error_reports_detected_value(self, run, packet_duration, which):
        run.return_value = SimpleNamespace(
            returncode=0,
            stdout='{"streams":[{"codec_type":"video","codec_name":"vp8"}],"format":{"duration":"110.0"}}',
        )
        upload = SimpleUploadedFile('run.webm', b'video bytes', content_type='video/webm')

        with self.assertRaisesMessage(ValidationError, 'detected as 110.00 seconds'):
            _probe_video(upload, 'video/webm')

    @override_settings(HOF_MAX_VIDEO_SECONDS=26)
    @patch('brainrot.validators.shutil.which', return_value='/usr/bin/ffprobe')
    @patch('brainrot.validators._packet_duration', return_value=23.0)
    @patch('brainrot.validators.subprocess.run')
    def test_probe_prefers_packet_span_over_incorrect_container_duration(
        self,
        run,
        packet_duration,
        which,
    ):
        run.return_value = SimpleNamespace(
            returncode=0,
            stdout='{"streams":[{"codec_type":"video","codec_name":"vp8"}],"format":{"duration":"110.0"}}',
        )
        upload = SimpleUploadedFile('run.webm', b'video bytes', content_type='video/webm')

        self.assertEqual(_probe_video(upload, 'video/webm'), 23.0)
        packet_duration.assert_called_once()

    def test_typing_result_has_share_box_and_url(self):
        response = self.client.get('/67/typing/')
        self.assertContains(response, 'typing.js?v=20260814.4')
        self.assertContains(response, 'id="typing-share-text"')
        self.assertContains(response, 'id="copy-typing-share"')

        script_path = finders.find('brainrot/typing.js')
        script = Path(script_path).read_text(encoding='utf-8')
        self.assertIn("new URL('/67/typing/', window.location.origin)", script)


@override_settings(TURNSTILE_ENABLED=False, HOF_SUBMISSIONS_PER_MINUTE=1)
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
    def test_valid_upload_is_published_and_rate_limited(self, validate):
        validate.return_value = ValidatedVideo('video/webm', 'webm', 23.0)
        self.client.login(username='scientist', password='test-password-67')
        video = SimpleUploadedFile('run.webm', b'video evidence', content_type='video/webm')
        response = self.client.post('/67/submit/', {'score': 67, 'video': video})
        self.assertEqual(response.status_code, 201)
        entry = HallOfFameEntry.objects.get()
        self.assertEqual(entry.state, HallOfFameEntry.State.APPROVED)
        self.assertIn(entry, self.client.get('/67/hall-of-fame/').context['entries'])

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

        download = self.client.get(f'{path}?download=1')
        self.assertEqual(download.status_code, 200)
        self.assertTrue(download['Content-Disposition'].startswith('attachment;'))
