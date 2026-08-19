from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .models import HallOfFameEntry


class SocialPrivacyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('privatepb', password='x')
        self.public_run = HallOfFameEntry.objects.create(
            user=self.user,
            score=120,
            video='hall_of_fame/public-pb.webm',
            mime_type='video/webm',
            duration_seconds=23,
            visibility=HallOfFameEntry.Visibility.PUBLIC,
        )
        self.private_run = HallOfFameEntry.objects.create(
            user=self.user,
            score=190,
            video='hall_of_fame/private-pb.webm',
            mime_type='video/webm',
            duration_seconds=23,
            visibility=HallOfFameEntry.Visibility.PRIVATE,
        )

    def test_public_hof_does_not_leak_private_pb(self):
        response = self.client.get('/67/hall-of-fame/?mode=six_seven')
        entry = list(response.context['entries'])[0]
        self.assertEqual(entry.id, self.public_run.id)
        self.assertEqual(entry.personal_best, 120)
        self.assertContains(response, 'PB 120')
        self.assertNotContains(response, 'PB 190')

    def test_private_owner_view_can_show_true_pb(self):
        self.client.force_login(self.user)
        response = self.client.get(f'/67/hall-of-fame/{self.private_run.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['entry'].personal_best, 190)
        self.assertContains(response, 'Best 190')

    def test_read_only_guest_view_does_not_create_reaction_session(self):
        guest = Client()
        response = guest.get(f'/67/hall-of-fame/{self.public_run.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(settings.SESSION_COOKIE_NAME, response.cookies)

    def test_first_guest_reaction_creates_session_and_can_be_remembered(self):
        guest = Client()
        response = guest.post('/67/reactions/toggle/', {
            'target_type': 'entry',
            'target_id': self.public_run.id,
            'emoji': '😋',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['active'])
        self.assertIn(settings.SESSION_COOKIE_NAME, response.cookies)

        detail = guest.get(f'/67/hall-of-fame/{self.public_run.id}/')
        active = [item for item in detail.context['entry'].reaction_items if item['emoji'] == '😋'][0]
        self.assertTrue(active['active'])
        self.assertEqual(active['count'], 1)
