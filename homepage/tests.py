from django.test import TestCase


class HomepageLayoutTests(TestCase):
    def test_hall_of_fame_is_featured_above_oi_archive(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('/67/hall-of-fame/', content)
        self.assertIn('featured-hof', content)
        self.assertIn('OI / competitive programming archive', content)
        self.assertLess(content.index('featured-hof'), content.index('OI / competitive programming archive'))
        self.assertLess(content.index('OI / competitive programming archive'), content.index('ORAC Leaderboards++'))
