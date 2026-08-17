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

        index = self.client.get('/67/')
        self.assertContains(index, '/67/counter/?mode=six_seven')
        self.assertContains(index, '/67/counter/?mode=leg_claps')
        self.assertContains(index, 'Tung Tung Leg Claps')
        self.assertNotContains(index, '酸黄瓜舞计数')
        self.assertNotContains(index, 'INSTITUTE OF NUMERICAL CULTURE')

    @override_settings(DEBUG=True)
    def test_counter_uses_shared_runtime_and_has_share_box(self):
        response = self.client.get('/67/counter/')
        self.assertContains(response, 'brainrot/counter_bootstrap.css')
        self.assertContains(response, 'brainrot/counter.js')
        self.assertNotContains(response, '?v=20260817.2')
        self.assertContains(response, 'id="counter-share-text"')
        self.assertContains(response, 'id="copy-counter-share"')
        self.assertContains(response, 'id="download-recording"')
        self.assertNotContains(response, 'Run classification')
        self.assertNotContains(response, 'Casual Run')
        self.assertContains(response, 'Submitting publishes the video for everyone to watch')
        self.assertContains(response, 'id="submit-hof"')
        self.assertContains(response, 'id="publication-modal"')
        self.assertContains(response, 'id="publication-consent"')
        self.assertContains(response, 'Anyone can watch, download and share it')
        self.assertContains(response, 'id="hof-display-name"')
        self.assertContains(response, 'id="start-run" disabled hidden')
        self.assertContains(response, 'id="counter-hof-portal"')
        self.assertContains(response, 'VIDEO LEADERBOARD')
        self.assertNotContains(response, 'PUBLIC VIDEO LEADERBOARD')
        self.assertNotContains(response, 'Run this foolish experiment again')
        self.assertNotContains(response, 'data-counter-mode=')
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
        self.assertIn("from './gesture_engine.js'", script)
        self.assertIn('let currentMode =', script)
        self.assertIn('createGestureTracker(currentMode)', script)
        self.assertIn('const GAME_SECONDS = 20;', script)
        self.assertIn('if (!running || now >= endTime) return;', script)
        self.assertNotIn('if (!running || now >= endTime || !sufficientlyVisible(landmarks)) return;', script)
        self.assertIn('gestureTracker.reset();', script)
        self.assertIn('setModeControlsDisabled(true);', script)
        self.assertIn('const blob = await stopRecording();', script)
        self.assertIn("recordingStream = recordingCanvas.captureStream(30);", script)
        self.assertIn('recorder = new MediaRecorder(recordingStream', script)
        self.assertNotIn('recorder = new MediaRecorder(stream', script)
        self.assertIn("form.append('event_timeline', JSON.stringify(eventTimeline));", script)
        self.assertIn("form.append('display_name', displayNameInput.value);", script)
        self.assertIn("form.append('publication_consent', 'yes');", script)
        self.assertIn("form.append('game_mode', currentMode);", script)
        self.assertIn('drawRecordingHud();', script)
        self.assertIn("'67 COUNT'", script)
        self.assertIn("hudBrand: 'icaijy.com'", script)
        self.assertNotIn('ICAiJY', script)
        self.assertNotIn('酸黄瓜舞计数', script)
        self.assertNotIn('pickle remains motionless', script)
        self.assertNotIn('Institute recommends', script)
        self.assertIn("const rawResponse = await response.text();", script)
        self.assertIn('payload = JSON.parse(rawResponse);', script)
        self.assertNotIn('await response.json()', script)
        self.assertIn("const preferCpu = /Firefox\\//.test(navigator.userAgent);", script)
        self.assertIn("delegate: preferCpu ? 'CPU' : 'GPU'", script)
        self.assertIn('I made ${score} 6️⃣7️⃣ moves in 20 seconds.', script)
        self.assertLess(script.index('enableButton.hidden = true;'), script.index('await initialisePoseRuntime();', script.index('async function initialiseDetector')))

        engine_path = finders.find('brainrot/gesture_engine.js')
        self.assertIsNotNone(engine_path)
        engine = Path(engine_path).read_text(encoding='utf-8')
        self.assertIn("LEG_CLAPS: 'leg_claps'", engine)
        self.assertIn('[23, 24, 25, 26]', engine)
        self.assertIn('LEG_CLAP_CLOSE_RATIO = 1.20', engine)
        self.assertIn('LEG_CLAP_REOPEN_RATIO = 1.35', engine)
        self.assertNotIn('LEG_CLAP_STABLE_FRAMES', engine)
        self.assertNotIn('stableSinceOpen', engine)

    def test_counter_modes_are_separate_entries_and_invalid_mode_falls_back(self):
        leg_claps = self.client.get('/67/counter/?mode=leg_claps')
        self.assertContains(leg_claps, 'data-game-mode="leg_claps"')
        self.assertContains(leg_claps, 'Tung Tung Leg Claps')
        self.assertNotContains(leg_claps, '酸黄瓜舞计数')
        self.assertContains(leg_claps, 'leg claps counted')
        self.assertNotContains(leg_claps, 'data-counter-mode=')

        six_seven = self.client.get('/67/counter/?mode=six_seven')
        self.assertContains(six_seven, 'data-game-mode="six_seven"')
        self.assertContains(six_seven, '67 Counter')

        fallback = self.client.get('/67/counter/?mode=not-a-real-experiment')
        self.assertContains(fallback, 'data-game-mode="six_seven"')

    def test_brainrot_pages_have_chinese_translation(self):
        response = self.client.get('/67/', HTTP_ACCEPT_LANGUAGE='zh-hans')
        self.assertContains(response, '酸黄瓜舞计数')
        counter = self.client.get('/67/counter/', HTTP_ACCEPT_LANGUAGE='zh-hans')
        self.assertContains(counter, '启用摄像头')
        self.assertContains(counter, '你的视频将会公开')
        leg_claps = self.client.get('/67/counter/?mode=leg_claps', HTTP_ACCEPT_LANGUAGE='zh-hans')
        self.assertContains(leg_claps, '酸黄瓜舞计数')


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
            visibility=HallOfFameEntry.Visibility.PUBLIC,
        )

    def test_detail_page_is_shareable_and_linked_from_leaderboard(self):
        detail_path = f'/67/hall-of-fame/{self.entry.id}/'
        response = self.client.get(detail_path)
        self.assertContains(response, 'id="hof-share-text"')
        self.assertContains(response, 'Share result!')
        self.assertContains(response, 'Copy share message')
        self.assertContains(response, f'/67/challenge/{self.entry.id}/')
        self.assertContains(response, 'swan-scientist made 3 6️⃣7️⃣ moves in 20 seconds.')
        self.assertContains(response, 'hof_detail.js?v=20260817.2')

        leaderboard = self.client.get('/67/hall-of-fame/')
        self.assertContains(leaderboard, detail_path)
        self.assertContains(leaderboard, f'/67/challenge/{self.entry.id}/')
        self.assertContains(leaderboard, 'Watch video preview')
        self.assertContains(leaderboard, 'preload="none"')
        self.assertContains(leaderboard, f'/67/hall-of-fame/{self.entry.id}/video/?download=1')
        self.assertContains(leaderboard, 'swan-scientist made 3 6️⃣7️⃣ moves in 20 seconds.')

        script_path = finders.find('brainrot/hof_detail.js')
        self.assertIsNotNone(script_path)
        script = Path(script_path).read_text(encoding='utf-8')
        self.assertIn('made ${score} 6️⃣7️⃣ moves in 20 seconds! 🔥', script)
        self.assertIn('made ${score} Tung Tung Leg Claps in 20 seconds! 🥒', script)
        self.assertIn("'🟩'.repeat(Math.min(score, 20))", script)
        self.assertIn('copyShareMessage', script)
        self.assertNotIn('navigator.clipboard.writeText(url)', script)

    def test_challenge_embeds_video_and_exact_event_timeline(self):
        response = self.client.get(f'/67/challenge/{self.entry.id}/')
        self.assertContains(response, 'id="rival-video"')
        self.assertContains(response, 'id="rival-score"')
        self.assertContains(response, 'Recorded event timeline ready')
        self.assertContains(response, '[1.2, 4.5, 9.67]')
        self.assertContains(response, 'data-rival-score="3"')
        self.assertContains(response, 'data-game-mode="six_seven"')

    def test_leaderboards_and_challenges_keep_game_modes_separate(self):
        leg_entry = HallOfFameEntry.objects.create(
            user=self.user,
            game_mode=HallOfFameEntry.GameMode.LEG_CLAPS,
            score=12,
            video='hall_of_fame/leg-claps.webm',
            mime_type='video/webm',
            duration_seconds=23,
            event_timeline=[float(value) for value in range(1, 13)],
            visibility=HallOfFameEntry.Visibility.PUBLIC,
        )
        six_seven_board = self.client.get('/67/hall-of-fame/')
        self.assertIn(self.entry, six_seven_board.context['entries'])
        self.assertNotIn(leg_entry, six_seven_board.context['entries'])

        leg_board = self.client.get('/67/hall-of-fame/?mode=leg_claps')
        self.assertIn(leg_entry, leg_board.context['entries'])
        self.assertNotIn(self.entry, leg_board.context['entries'])
        self.assertContains(leg_board, 'made 12 leg claps in 20 seconds')

        challenge = self.client.get(f'/67/challenge/{leg_entry.id}/')
        self.assertContains(challenge, 'data-game-mode="leg_claps"')
        self.assertContains(challenge, 'Challenge mode:')
        self.assertNotContains(challenge, 'data-counter-mode="six_seven"')

    def test_legacy_challenge_uses_labelled_estimated_pace(self):
        self.entry.event_timeline = []
        self.entry.save(update_fields=['event_timeline'])
        response = self.client.get(f'/67/challenge/{self.entry.id}/')
        self.assertContains(response, 'Legacy run · estimated count pace')

    def test_non_public_entry_has_no_detail_or_challenge(self):
        self.entry.visibility = HallOfFameEntry.Visibility.PRIVATE
        self.entry.save(update_fields=['visibility'])
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
            visibility=HallOfFameEntry.Visibility.PUBLIC,
        )
        detail = self.client.get(f'/67/hall-of-fame/{anonymous.id}/')
        self.assertContains(detail, 'Nameless Researcher')
        self.assertContains(detail, 'guest')
        self.assertContains(detail, 'contact the site owner')
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
        self.assertContains(response, 'typing.js?v=20260817.1')
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

    def test_upload_requires_explicit_publication_consent(self):
        self.client.login(username='scientist', password='test-password-67')
        response = self.client.post('/67/submit/', {'score': 67})
        self.assertEqual(response.status_code, 400)
        self.assertIn('confirm', response.json()['error'])
        self.assertEqual(HallOfFameEntry.objects.count(), 0)

    def test_publication_consent_error_is_localized(self):
        self.client.login(username='scientist', password='test-password-67')
        response = self.client.post(
            '/67/submit/',
            {'score': 67},
            HTTP_ACCEPT_LANGUAGE='zh-hans',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('公开发布', response.json()['error'])

    def test_invalid_counter_mode_is_rejected(self):
        self.client.login(username='scientist', password='test-password-67')
        response = self.client.post('/67/submit/', {
            'score': 1,
            'game_mode': 'knees_everywhere',
            'publication_consent': 'yes',
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Invalid counter mode.')

    @patch('brainrot.views.validate_hall_of_fame_video')
    def test_anonymous_upload_is_published_and_rate_limited_by_client(self, validate):
        validate.return_value = ValidatedVideo('video/webm', 'webm', 23.0)
        video = SimpleUploadedFile('run.webm', b'anonymous evidence', content_type='video/webm')
        response = self.client.post('/67/submit/', {
            'score': 3,
            'display_name': '  Anonymous   Swan  67 ',
            'event_timeline': json.dumps([1.2, 4.5, 9.67]),
            'publication_consent': 'yes',
            'video': video,
        }, REMOTE_ADDR='203.0.113.67')
        self.assertEqual(response.status_code, 201)
        entry = HallOfFameEntry.objects.get()
        self.assertIsNone(entry.user)
        self.assertEqual(entry.display_name, 'Anonymous Swan 67')
        self.assertIn('send the public link', response.json()['message'])

        attempt = HallOfFameUploadAttempt.objects.get()
        self.assertEqual(len(attempt.client_key), 64)
        self.assertNotIn('203.0.113.67', attempt.client_key)

        second = SimpleUploadedFile('run.webm', b'more evidence', content_type='video/webm')
        response = self.client.post('/67/submit/', {'score': 68, 'video': second}, REMOTE_ADDR='203.0.113.67')
        self.assertEqual(response.status_code, 429)

    def test_anonymous_name_cannot_impersonate_registered_user(self):
        response = self.client.post('/67/submit/', {
            'score': 1,
            'display_name': 'ＳＣＩＥＮＴＩＳＴ',
            'event_timeline': '[1.0]',
            'publication_consent': 'yes',
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('registered user', response.json()['error'])
        self.assertEqual(HallOfFameEntry.objects.count(), 0)

    def test_anonymous_name_cannot_claim_reserved_admin_role(self):
        response = self.client.post('/67/submit/', {
            'score': 1,
            'display_name': 'ＡＤＭＩＮ',
            'event_timeline': '[1.0]',
            'publication_consent': 'yes',
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn('reserved site role', response.json()['error'])

    @patch('brainrot.views.validate_hall_of_fame_video')
    def test_valid_upload_is_published_and_rate_limited(self, validate):
        validate.return_value = ValidatedVideo('video/webm', 'webm', 23.0)
        self.client.login(username='scientist', password='test-password-67')
        video = SimpleUploadedFile('run.webm', b'video evidence', content_type='video/webm')
        response = self.client.post('/67/submit/', {
            'score': 3,
            'event_timeline': json.dumps([1.2, 4.5, 9.67]),
            'publication_consent': 'yes',
            'video': video,
        })
        self.assertEqual(response.status_code, 201)
        entry = HallOfFameEntry.objects.get()
        self.assertEqual(entry.user, self.user)
        self.assertEqual(entry.display_name, '')
        self.assertEqual(entry.game_mode, HallOfFameEntry.GameMode.SIX_SEVEN)
        self.assertEqual(entry.visibility, HallOfFameEntry.Visibility.PUBLIC)
        self.assertEqual(entry.event_timeline, [1.2, 4.5, 9.67])
        self.assertEqual(response.json()['entry_url'], f'/67/hall-of-fame/{entry.id}/')
        self.assertIn(entry, self.client.get('/67/hall-of-fame/').context['entries'])

        second = SimpleUploadedFile('run.webm', b'more evidence', content_type='video/webm')
        response = self.client.post('/67/submit/', {'score': 68, 'video': second})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(HallOfFameEntry.objects.count(), 1)

    @patch('brainrot.views.validate_hall_of_fame_video')
    def test_leg_clap_upload_keeps_an_explicit_mode(self, validate):
        validate.return_value = ValidatedVideo('video/webm', 'webm', 23.0)
        self.client.login(username='scientist', password='test-password-67')
        video = SimpleUploadedFile('leg-claps.webm', b'knee evidence', content_type='video/webm')
        response = self.client.post('/67/submit/', {
            'game_mode': HallOfFameEntry.GameMode.LEG_CLAPS,
            'score': 2,
            'event_timeline': '[4.2, 12.5]',
            'publication_consent': 'yes',
            'video': video,
        })
        self.assertEqual(response.status_code, 201)
        entry = HallOfFameEntry.objects.get()
        self.assertEqual(entry.game_mode, HallOfFameEntry.GameMode.LEG_CLAPS)
        self.assertIn(entry, self.client.get('/67/hall-of-fame/?mode=leg_claps').context['entries'])
        self.assertNotIn(entry, self.client.get('/67/hall-of-fame/').context['entries'])

    def test_private_video_is_owner_only_then_public(self):
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
        entry.visibility = HallOfFameEntry.Visibility.PUBLIC
        entry.save(update_fields=['visibility'])
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
        self.superuser = get_user_model().objects.create_superuser(
            'super-67',
            password='super-password-67',
            email='super@example.com',
        )
        self.entry = HallOfFameEntry.objects.create(
            user=self.owner,
            score=67,
            video=SimpleUploadedFile('owned.webm', b'owned evidence', content_type='video/webm'),
            mime_type='video/webm',
            duration_seconds=23,
            visibility=HallOfFameEntry.Visibility.PUBLIC,
        )
        self.anonymous = HallOfFameEntry.objects.create(
            display_name='No Account',
            score=61,
            video=SimpleUploadedFile('anonymous.webm', b'anonymous evidence', content_type='video/webm'),
            mime_type='video/webm',
            duration_seconds=23,
            visibility=HallOfFameEntry.Visibility.PUBLIC,
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
        self.assertContains(detail, 'Make private')
        self.assertContains(detail, '>Delete<')

    def test_owner_can_delete_entry_and_video(self):
        video_name = self.entry.video.name
        self.assertTrue(self.entry.video.storage.exists(video_name))
        self.client.login(username='owner', password='owner-password-67')

        response = self.client.post(f'/67/hall-of-fame/{self.entry.id}/delete/')
        self.assertRedirects(response, '/67/hall-of-fame/mine/?deleted=1')
        self.assertFalse(HallOfFameEntry.objects.filter(pk=self.entry.id).exists())
        self.assertFalse(self.entry.video.storage.exists(video_name))

    def test_delete_control_returns_to_management_instead_of_deleted_detail(self):
        self.client.login(username='owner', password='owner-password-67')
        detail = self.client.get(f'/67/hall-of-fame/{self.entry.id}/')
        self.assertContains(
            detail,
            'name="next" value="/67/hall-of-fame/mine/?deleted=1"',
        )

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

    def test_owner_can_make_entry_private_and_public_again(self):
        self.client.login(username='owner', password='owner-password-67')
        url = f'/67/hall-of-fame/{self.entry.id}/visibility/'
        response = self.client.post(url, {'visibility': 'private'})
        self.assertRedirects(response, '/67/hall-of-fame/mine/?updated=1')
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.visibility, HallOfFameEntry.Visibility.PRIVATE)
        leaderboard = self.client.get('/67/hall-of-fame/')
        self.assertNotIn(self.entry, leaderboard.context['entries'])
        self.assertEqual(self.client.get(f'/67/hall-of-fame/{self.entry.id}/').status_code, 200)

        self.client.logout()
        self.assertEqual(self.client.get(f'/67/hall-of-fame/{self.entry.id}/').status_code, 404)
        self.client.login(username='owner', password='owner-password-67')
        self.client.post(url, {'visibility': 'public'})
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.visibility, HallOfFameEntry.Visibility.PUBLIC)

    def test_other_user_cannot_change_visibility(self):
        self.client.login(username='other', password='other-password-67')
        response = self.client.post(
            f'/67/hall-of-fame/{self.entry.id}/visibility/',
            {'visibility': 'private'},
        )
        self.assertEqual(response.status_code, 404)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.visibility, HallOfFameEntry.Visibility.PUBLIC)

    def test_superuser_can_manage_every_entry_in_site_ui(self):
        self.anonymous.visibility = HallOfFameEntry.Visibility.PRIVATE
        self.anonymous.save(update_fields=['visibility'])
        self.client.login(username='super-67', password='super-password-67')

        management = self.client.get('/67/hall-of-fame/mine/')
        self.assertContains(management, 'SUPERUSER HALL OF FAME CONTROL')
        self.assertContains(management, 'No Account')
        self.assertContains(management, f'/67/hall-of-fame/{self.anonymous.id}/visibility/')
        self.assertEqual(self.client.get(f'/67/hall-of-fame/{self.anonymous.id}/').status_code, 200)
        self.assertEqual(self.client.get(f'/67/hall-of-fame/{self.anonymous.id}/video/').status_code, 200)

        response = self.client.post(
            f'/67/hall-of-fame/{self.anonymous.id}/visibility/',
            {'visibility': 'public'},
        )
        self.assertRedirects(response, '/67/hall-of-fame/mine/?updated=1')
        self.anonymous.refresh_from_db()
        self.assertEqual(self.anonymous.visibility, HallOfFameEntry.Visibility.PUBLIC)

        response = self.client.post(f'/67/hall-of-fame/{self.anonymous.id}/delete/')
        self.assertRedirects(response, '/67/hall-of-fame/mine/?deleted=1')
        self.assertFalse(HallOfFameEntry.objects.filter(pk=self.anonymous.id).exists())
