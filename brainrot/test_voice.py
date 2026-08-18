from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import HallOfFameEntry


class VoiceSpeedrunPageTests(TestCase):
    def test_index_and_voice_page_expose_the_new_game(self):
        index = self.client.get('/67/')
        self.assertEqual(index.status_code, 200)
        self.assertContains(index, '/67/voice/')
        self.assertContains(index, 'Six Seven Voice Speedrun')

        voice = self.client.get('/67/voice/')
        self.assertEqual(voice.status_code, 200)
        self.assertContains(voice, 'id="voice-app"')
        self.assertContains(voice, 'data-game-mode="voice_67"')
        self.assertContains(voice, 'voice_counter.js')
        self.assertContains(voice, 'Local model hearing')
        self.assertContains(voice, 'camera + microphone')
        self.assertContains(voice, 'Recognition runs locally in this browser')
        self.assertNotContains(voice, "browser vendor's speech service")

    def test_voice_is_a_real_hall_of_fame_mode(self):
        voice_entry = HallOfFameEntry.objects.create(
            display_name='Fast Mouth',
            game_mode=HallOfFameEntry.GameMode.VOICE_67,
            score=12,
            video='hall_of_fame/voice.webm',
            mime_type='video/webm',
            duration_seconds=23.25,
            event_timeline=[round(index * 1.5, 3) for index in range(1, 13)],
            visibility=HallOfFameEntry.Visibility.PUBLIC,
        )
        HallOfFameEntry.objects.create(
            display_name='Arms Only',
            game_mode=HallOfFameEntry.GameMode.SIX_SEVEN,
            score=99,
            video='hall_of_fame/arms.webm',
            mime_type='video/webm',
            duration_seconds=23.25,
            event_timeline=[],
            visibility=HallOfFameEntry.Visibility.PUBLIC,
        )

        response = self.client.get('/67/hall-of-fame/?mode=voice_67')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Voice 67 Hall of Fame')
        self.assertContains(response, 'Fast Mouth')
        self.assertContains(response, 'said “six seven” 12 times')
        self.assertNotContains(response, 'Arms Only')
        self.assertContains(response, f'/67/voice/?rival={voice_entry.id}')

    def test_generic_challenge_dispatches_voice_but_preserves_pose_runner(self):
        voice_entry = HallOfFameEntry.objects.create(
            display_name='Voice Rival',
            game_mode=HallOfFameEntry.GameMode.VOICE_67,
            score=3,
            video='hall_of_fame/voice-rival.webm',
            mime_type='video/webm',
            duration_seconds=23.25,
            event_timeline=[3.0, 6.0, 9.0],
            visibility=HallOfFameEntry.Visibility.PUBLIC,
        )
        pose_entry = HallOfFameEntry.objects.create(
            display_name='Pose Rival',
            game_mode=HallOfFameEntry.GameMode.SIX_SEVEN,
            score=2,
            video='hall_of_fame/pose-rival.webm',
            mime_type='video/webm',
            duration_seconds=23.25,
            event_timeline=[5.0, 10.0],
            visibility=HallOfFameEntry.Visibility.PUBLIC,
        )

        voice_challenge = self.client.get(f'/67/challenge/{voice_entry.id}/')
        self.assertRedirects(
            voice_challenge,
            f'/67/voice/?rival={voice_entry.id}',
            fetch_redirect_response=False,
        )

        pose_challenge = self.client.get(f'/67/challenge/{pose_entry.id}/')
        self.assertEqual(pose_challenge.status_code, 200)
        self.assertContains(pose_challenge, 'id="counter-app"')
        self.assertContains(pose_challenge, 'Pose Rival')

    def test_voice_challenge_rejects_non_voice_rival_parameter(self):
        user = get_user_model().objects.create_user('pose-user')
        pose_entry = HallOfFameEntry.objects.create(
            user=user,
            game_mode=HallOfFameEntry.GameMode.LEG_CLAPS,
            score=4,
            video='hall_of_fame/leg-rival.webm',
            mime_type='video/webm',
            duration_seconds=23.25,
            event_timeline=[2.0, 4.0, 6.0, 8.0],
            visibility=HallOfFameEntry.Visibility.PUBLIC,
        )

        response = self.client.get(f'/67/voice/?rival={pose_entry.id}')
        self.assertEqual(response.status_code, 404)
