from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Cosmetic, HallOfFameComment, HallOfFameEntry, UserCosmetic


class SocialSurfaceTests(TestCase):
    def entry(self, user, score, visibility='public'):
        return HallOfFameEntry.objects.create(
            user=user,
            game_mode='six_seven',
            score=score,
            video='hall_of_fame/test.mp4',
            mime_type='video/mp4',
            duration_seconds=20,
            event_timeline=[],
            visibility=visibility,
        )

    def test_admin_can_equip_any_cosmetic_for_free(self):
        User = get_user_model()
        admin = User.objects.create_superuser(username='centralbank', email='admin@example.com', password='x')
        cosmetic = Cosmetic.objects.create(name='Admin Aura', slug='admin-aura', category='username')
        self.client.force_login(admin)
        response = self.client.post(f'/67/shop/equip/{cosmetic.pk}/', {'next': '/67/shop/'})
        self.assertEqual(response.status_code, 302)
        owned = UserCosmetic.objects.get(user=admin, cosmetic=cosmetic)
        self.assertIsNone(owned.expires_at)
        self.assertEqual(admin.equipped_cosmetics.get(category='username').cosmetic_id, cosmetic.pk)

    def test_latest_comments_hides_private_threads(self):
        User = get_user_model()
        alice = User.objects.create_user(username='alice67', password='x')
        bob = User.objects.create_user(username='bob67', password='x')
        public_entry = self.entry(alice, 150, 'public')
        private_entry = self.entry(bob, 160, 'private')
        HallOfFameComment.objects.create(entry=public_entry, user=alice, author_name='alice67', body='public hello')
        HallOfFameComment.objects.create(entry=private_entry, user=bob, author_name='bob67', body='private hello')
        response = self.client.get('/67/comments/')
        self.assertContains(response, 'public hello')
        self.assertNotContains(response, 'private hello')

    def test_daily_mini_returns_best_today(self):
        User = get_user_model()
        alice = User.objects.create_user(username='alice67', password='x')
        bob = User.objects.create_user(username='bob67', password='x')
        self.entry(alice, 150, 'private')
        self.entry(bob, 140, 'public')
        response = self.client.get('/67/daily-mini/')
        self.assertEqual(response.status_code, 200)
        first = response.json()['entries'][0]
        self.assertEqual((first['name'], first['score'], first['private']), ('alice67', 150, True))
