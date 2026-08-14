import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .models import HallOfFameEntry, HallOfFameUploadAttempt
from .validators import ValidatedVideo, _packet_duration, _probe_video
from .views import _validated_event_timeline


class BrainrotPageTests(TestCase):
    def test_public_pages_load(self):
        for path in ('/67/', '/67/counter/', '/67/hall-of-fame/', '/67/typing/'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

        legacy = self.client.get('/67/games/')
        self.assertEqual(legacy.status_code, 301)
        self.assertEqual(legacy['Location'], '/67/')

    @override_settings(DEBUG=True)
    def test_counter_uses_cache_busted_runtime_and_has_share_box(self):
        response = self.client.get('/67/counter/')
        self.assertContains(response, 'brainrot.css?v=20260814.7')
        self.assertContains(response, 'counter.js?v=20260814.12')
        self.assertContains(response, 'id="counter-share-text"')
        self.assertContains(response, 'id="copy-counter-share"')
        self.assertContains(response, 'id="download-recording"')
        self.assertNotContains(response, 'Run classification')
        self.assertNotContains(response, 'Casual Run')
        self.assertContains(response, 'nothing uploads unless you press Submit to Hall of Fame')
        self.assertContains(response, 'id="submit-hof"')
        self.assertContains(response, 'id="hof-display-name"')
        self.assertNotContains(response, 'Log in to submit this run')

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
        self.assertIn("recordingStream = recordingCanvas.captureStream(30);", script)
        self.assertIn('recorder = new MediaRecorder(recordingStream', script)
        self.assertNotIn('recorder = new MediaRecorder(stream', script)
        self.assertIn("form.append('event_timeline', JSON.stringify(eventTimeline));", script)
        self.assertIn("form.append('display_name', displayNameInput.value);", script)


class HallOfFamePageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('swan-scientist')
        self.entry = HallOfFameEntry.objects.create(
            user=self.user,
            score=3,
            video='hall_of_fame/specimen.webm',
            mime_type='video/webm',
            duration_seconds=23.25,
            event_timeline=[1.2, 4.5, 9.67],
            state=HallOfFameEntry.State.APPROVED,
        )

    def test_detail_page_is_shareable_and_linked_from_leaderboard(self):
        detail_path = f'/67/hall-of-fame/{self.entry.id}/'
        response = self.client.get(detail_path)
        self.assertContains(response, 'id="hof-share-text"')
        self.assertContains(response, 'Share Hall of Fame link')
        self.assertContains(response, f'/67/challenge/{self.entry.id}/')
        self.assertContains(response, 'hof_detail.js?v=20260814.1')

        leaderboard = self.client.get('/67/hall-of-fame/')
        self.assertContains(leaderboard, detail_path)
        self.assertContains(leaderboard, f'/67/challenge/{self.entry.id}/')

    def test_challenge_embeds_video_and_exact_event_timeline(self):
        response = self.client.get(f'/67/challenge/{self.entry.id}/')
        self.assertContains(response, 'id="rival-video"')
        self.assertContains(response, 'id="rival-score"')
        self.assertContains(response, 'Recorded event timeline ready')
        self.assertContains(response, '[1.2, 4.5, 9.67]')
        self.assertContains(response, 'data-rival-score="3"')

    def test_legacy_challenge_uses_labelled_estimated_pace(self):
        self.entry.event_timeline = []
        self.entry.save(update_fields=['event_timeline'])
        response = self.client.get(f'/67/challenge/{self.entry.id}/')
        self.assertContains(response, 'Legacy run · estimated count pace')

    def test_non_public_entry_has_no_detail_or_challenge(self):
        self.entry.state = HallOfFameEntry.State.REJECTED
        self.entry.save(update_fields=['state'])
        self.assertEqual(self.client.get(f'/67/hall-of-fame/{self.entry.id}/').status_code, 404)
        self.assertEqual(self.client.get(f'/67/challenge/{self.entry.id}/').status_code, 404)

    def test_anonymous_entry_uses_its_public_display_name(self):
        anonymous = HallOfFameEntry.objects.create(
            user=None,
            display_name='Nameless Researcher',
            score=67,
            video='hall_of_fame/anonymous.webm',
            mime_type='video/webm',
            duration_seconds=23,
            state=HallOfFameEntry.State.APPROVED,
        )
        detail = self.client.get(f'/67/hall-of-fame/{anonymous.id}/')
        self.assertContains(detail, 'Nameless Researcher')
        self.assertNotContains(detail, 'Delete my entry')

        challenge = self.client.get(f'/67/challenge/{anonymous.id}/')
        self.assertContains(challenge, 'YOU vs Nameless Researcher')


class EventTimelineValidationTests(TestCase):
    def test_valid_timeline_is_normalised(self):
        self.assertEqual(_validated_event_timeline('[1.23456, 9, 20.0]', 3), [1.235, 9.0, 20.0])

    def test_timeline_must_match_score_and_be_monotonic(self):
        with self.assertRaisesMessage(ValidationError, 'does not match'):
            _validated_event_timeline('[1.0]', 2)
        with self.assertRaisesMessage(ValidationError, 'invalid timestamp'):
            _validated_event_timeline('[4.0, 3.0]', 2)


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


@override_settings(DEBUG=True, TURNSTILE_ENABLED=False, HOF_SUBMISSIONS_PER_MINUTE=1)
class HallOfFameSubmissionTests(TestCase):
    def setUp(self):
        self.private_directory = tempfile.TemporaryDirectory()
        self.override = override_settings(PRIVATE_MEDIA_ROOT=self.private_directory.name)
        self.override.enable()
        self.user = get_user_model().objects.create_user('scientist', password='test-password-67')

    def tearDown(self):
        self.override.disable()
        self.private_directory.cleanup()

    @override_settings(DEBUG=False, TURNSTILE_ENABLED=False)
    def test_production_anonymous_upload_requires_turnstile(self):
        response = self.client.post('/67/submit/', {'score': 67})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(HallOfFameUploadAttempt.objects.count(), 0)

    @patch('brainrot.views.validate_hall_of_fame_video')
    def test_anonymous_upload_is_published_and_rate_limited_by_client(self, validate):
        validate.return_value = ValidatedVideo('video/webm', 'webm', 23.0)
        video = SimpleUploadedFile('run.webm', b'anonymous evidence', content_type='video/webm')
        response = self.client.post('/67/submit/', {
            'score': 3,
            'display_name': '  Anonymous   Swan  67 ',
            'event_timeline': json.dumps([1.2, 4.5, 9.67]),
            'video': video,
        }, REMOTE_ADDR='203.0.113.67')
        self.assertEqual(response.status_code, 201)
        entry = HallOfFameEntry.objects.get()
        self.assertIsNone(entry.user)
        self.assertEqual(entry.display_name, 'Anonymous Swan 67')
        self.assertIn('cannot be managed later', response.json()['message'])

        attempt = HallOfFameUploadAttempt.objects.get()
        self.assertEqual(len(attempt.client_key), 64)
        self.assertNotIn('203.0.113.67', attempt.client_key)

        second = SimpleUploadedFile('run.webm', b'more evidence', content_type='video/webm')
        response = self.client.post('/67/submit/', {'score': 68, 'video': second}, REMOTE_ADDR='203.0.113.67')
        self.assertEqual(response.status_code, 429)

    @patch('brainrot.views.validate_hall_of_fame_video')
    def test_valid_upload_is_published_and_rate_limited(self, validate):
        validate.return_value = ValidatedVideo('video/webm', 'webm', 23.0)
        self.client.login(username='scientist', password='test-password-67')
        video = SimpleUploadedFile('run.webm', b'video evidence', content_type='video/webm')
        response = self.client.post('/67/submit/', {
            'score': 3,
            'event_timeline': json.dumps([1.2, 4.5, 9.67]),
            'video': video,
        })
        self.assertEqual(response.status_code, 201)
        entry = HallOfFameEntry.objects.get()
        self.assertEqual(entry.user, self.user)
        self.assertEqual(entry.display_name, '')
        self.assertEqual(entry.state, HallOfFameEntry.State.APPROVED)
        self.assertEqual(entry.event_timeline, [1.2, 4.5, 9.67])
        self.assertEqual(response.json()['entry_url'], f'/67/hall-of-fame/{entry.id}/')
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


class HallOfFameOwnershipTests(TestCase):
    def setUp(self):
        self.private_directory = tempfile.TemporaryDirectory()
        self.override = override_settings(PRIVATE_MEDIA_ROOT=self.private_directory.name)
        self.override.enable()
        self.owner = get_user_model().objects.create_user('owner', password='owner-password-67')
        self.other = get_user_model().objects.create_user('other', password='other-password-67')
        self.entry = HallOfFameEntry.objects.create(
            user=self.owner,
            score=67,
            video=SimpleUploadedFile('owned.webm', b'owned evidence', content_type='video/webm'),
            mime_type='video/webm',
            duration_seconds=23,
            state=HallOfFameEntry.State.APPROVED,
        )
        self.anonymous = HallOfFameEntry.objects.create(
            display_name='No Account',
            score=61,
            video=SimpleUploadedFile('anonymous.webm', b'anonymous evidence', content_type='video/webm'),
            mime_type='video/webm',
            duration_seconds=23,
            state=HallOfFameEntry.State.APPROVED,
        )

    def tearDown(self):
        self.override.disable()
        self.private_directory.cleanup()

    def test_my_hof_requires_login_and_lists_only_owned_runs(self):
        response = self.client.get('/67/hall-of-fame/mine/')
        self.assertEqual(response.status_code, 302)

        self.client.login(username='owner', password='owner-password-67')
        response = self.client.get('/67/hall-of-fame/mine/')
        self.assertContains(response, f'/67/hall-of-fame/{self.entry.id}/')
        self.assertNotContains(response, 'No Account')
        self.assertContains(response, f'/67/hall-of-fame/{self.entry.id}/delete/')

        detail = self.client.get(f'/67/hall-of-fame/{self.entry.id}/')
        self.assertContains(detail, 'Delete my entry &amp; video')

    def test_owner_can_delete_entry_and_video(self):
        video_name = self.entry.video.name
        self.assertTrue(self.entry.video.storage.exists(video_name))
        self.client.login(username='owner', password='owner-password-67')

        response = self.client.post(f'/67/hall-of-fame/{self.entry.id}/delete/')
        self.assertRedirects(response, '/67/hall-of-fame/mine/?deleted=1')
        self.assertFalse(HallOfFameEntry.objects.filter(pk=self.entry.id).exists())
        self.assertFalse(self.entry.video.storage.exists(video_name))

    def test_other_user_and_anonymous_request_cannot_delete(self):
        delete_url = f'/67/hall-of-fame/{self.entry.id}/delete/'
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)

        self.client.login(username='other', password='other-password-67')
        self.assertEqual(self.client.post(delete_url).status_code, 404)
        self.assertTrue(HallOfFameEntry.objects.filter(pk=self.entry.id).exists())

    def test_anonymous_entry_has_no_owner_delete_control(self):
        self.client.login(username='owner', password='owner-password-67')
        detail = self.client.get(f'/67/hall-of-fame/{self.anonymous.id}/')
        self.assertNotContains(detail, 'Delete my entry')
        self.assertEqual(
            self.client.post(f'/67/hall-of-fame/{self.anonymous.id}/delete/').status_code,
            404,
        )
