from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .economy import _settle_day, balances_for, hof_asset_value_67, leaderboard, purchase_offer
from .models import Cosmetic, CosmeticOffer, DailySettlement, HallOfFameEntry


class EconomyV1Tests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.alice = User.objects.create_user(username='alice67', password='x')
        self.bob = User.objects.create_user(username='bob67', password='x')

    def entry(self, user, score, visibility='public', mode='six_seven'):
        return HallOfFameEntry.objects.create(
            user=user,
            game_mode=mode,
            score=score,
            video='hall_of_fame/test.mp4',
            mime_type='video/mp4',
            duration_seconds=20,
            event_timeline=[],
            visibility=visibility,
        )

    def test_public_and_private_asset_values(self):
        private = self.entry(self.alice, 170, 'private')
        self.assertEqual(private.asset_value_67, 6)
        self.assertEqual(balances_for(self.alice)['67'], 6)

        private.visibility = 'public'
        private.save(update_fields=['visibility'])
        private.refresh_from_db()
        self.assertEqual(private.asset_value_67, 9)
        self.assertEqual(balances_for(self.alice)['67'], 9)

    def test_spend_then_privativise_and_delete_creates_debt(self):
        entry = self.entry(self.alice, 170, 'public')
        cosmetic = Cosmetic.objects.create(name='Debt Machine', slug='debt-machine', category='username')
        offer = CosmeticOffer.objects.create(cosmetic=cosmetic, currency='67', price=9, duration_days=7)
        purchase_offer(self.alice, offer)
        self.assertEqual(balances_for(self.alice)['67'], 0)

        entry.visibility = 'private'
        entry.save(update_fields=['visibility'])
        self.assertEqual(balances_for(self.alice)['67'], -3)

        entry.delete()
        self.assertEqual(balances_for(self.alice)['67'], -9)

    def test_debt_cannot_be_used_for_more_purchases(self):
        entry = self.entry(self.alice, 170, 'public')
        cosmetic = Cosmetic.objects.create(name='First', slug='first', category='username')
        first = CosmeticOffer.objects.create(cosmetic=cosmetic, currency='67', price=9, duration_days=7)
        purchase_offer(self.alice, first)
        entry.visibility = 'private'
        entry.save(update_fields=['visibility'])
        self.assertEqual(balances_for(self.alice)['67'], -3)

        second_cosmetic = Cosmetic.objects.create(name='Second', slug='second', category='badge')
        second = CosmeticOffer.objects.create(cosmetic=second_cosmetic, currency='67', price=1, duration_days=7)
        with self.assertRaises(ValueError):
            purchase_offer(self.alice, second)

    def test_non_main_modes_do_not_back_67_coin(self):
        combo = self.entry(self.alice, 7000, 'public', 'combine')
        combo.refresh_from_db()
        self.assertEqual(combo.asset_value_67, 0)
        self.assertEqual(balances_for(self.alice)['67'], 0)

    def test_daily_keeps_best_per_user_and_allows_private(self):
        self.entry(self.alice, 100, 'public')
        best = self.entry(self.alice, 150, 'private')
        second = self.entry(self.bob, 140, 'public')
        rows = leaderboard('today', 'six_seven')
        self.assertEqual([row.pk for row in rows[:2]], [best.pk, second.pk])

    def test_daily_settlement_is_idempotent(self):
        first = self.entry(self.alice, 150, 'private')
        second = self.entry(self.bob, 140, 'public')
        yesterday = timezone.localdate() - timedelta(days=1)
        tz = timezone.get_current_timezone()
        stamp = timezone.make_aware(datetime.combine(yesterday, time(hour=12)), tz)
        HallOfFameEntry.objects.filter(pk__in=[first.pk, second.pk]).update(created_at=stamp)

        self.assertTrue(_settle_day(yesterday))
        self.assertFalse(_settle_day(yesterday))
        self.assertEqual(balances_for(self.alice)['61'], 20)
        self.assertEqual(balances_for(self.bob)['61'], 13)
        self.assertEqual(DailySettlement.objects.get(date=yesterday).distributed, 33)
