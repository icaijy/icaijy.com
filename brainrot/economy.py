import uuid
from datetime import datetime, time, timedelta

from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.utils import timezone

from .models import (
    Cosmetic,
    CurrencyBalance,
    CurrencyTransaction,
    DailySettlement,
    EquippedCosmetic,
    HallOfFameEntry,
    UserCosmetic,
)


DAILY_61_PRIZES = (20, 13, 9, 7, 5, 4, 3)


def _day_bounds(day):
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, time.min), tz)
    return start, start + timedelta(days=1)


def hof_asset_value_67(entry):
    """Current 67-Coin backing value of one HOF entry.

    Only the main 67 mode backs currency in v1. Private runs retain a smaller
    achievement value; public runs receive roughly a 50% publication premium.
    """
    if not entry.user_id or entry.game_mode != HallOfFameEntry.GameMode.SIX_SEVEN or entry.score <= 0:
        return 0
    base = max(1, (entry.score * entry.score) // (67 * 67))
    if entry.visibility == HallOfFameEntry.Visibility.PUBLIC:
        return base + max(1, base // 2)
    return base


def post_transaction(*, user, currency, amount, reason, unique_key, hall_entry=None, metadata=None, allow_negative=False):
    """Post an idempotent wallet transaction and update the cached balance.

    User purchases cannot create debt. HOF revaluations may create debt because
    a user is allowed to privatise or delete an asset after spending against it.
    """
    if amount == 0:
        return None
    with transaction.atomic():
        existing = CurrencyTransaction.objects.filter(unique_key=unique_key).first()
        if existing:
            return existing

        balance, _ = CurrencyBalance.objects.get_or_create(
            user=user,
            currency=currency,
            defaults={'balance': 0, 'lifetime_earned': 0},
        )
        balance = CurrencyBalance.objects.select_for_update().get(pk=balance.pk)
        if not allow_negative and balance.balance + amount < 0:
            raise ValueError('Insufficient balance. The 67 Central Bank has declined your card.')

        txn = CurrencyTransaction.objects.create(
            user=user,
            currency=currency,
            amount=amount,
            reason=reason,
            unique_key=unique_key,
            hall_entry=hall_entry,
            metadata=metadata or {},
        )
        balance.balance = F('balance') + amount
        if amount > 0:
            balance.lifetime_earned = F('lifetime_earned') + amount
        balance.save(update_fields=['balance', 'lifetime_earned', 'updated_at'])
        return txn


def sync_hof_asset_value(entry):
    """Revalue one persisted HOF asset and post only the delta."""
    if not entry.pk:
        return
    with transaction.atomic():
        locked = HallOfFameEntry.objects.select_for_update().get(pk=entry.pk)
        desired = hof_asset_value_67(locked)
        previous = locked.asset_value_67
        if desired == previous:
            return
        revision = locked.asset_revision + 1
        HallOfFameEntry.objects.filter(pk=locked.pk).update(
            asset_value_67=desired,
            asset_revision=revision,
        )
        entry.asset_value_67 = desired
        entry.asset_revision = revision
        if locked.user_id:
            post_transaction(
                user=locked.user,
                currency=CurrencyTransaction.Currency.SIXTY_SEVEN,
                amount=desired - previous,
                reason='HOF asset revaluation',
                unique_key=f'hof-asset:{locked.pk}:{revision}',
                hall_entry=locked,
                metadata={
                    'entry_id': locked.pk,
                    'score': locked.score,
                    'visibility': locked.visibility,
                    'old_value': previous,
                    'new_value': desired,
                },
                allow_negative=True,
            )


def remove_hof_asset(entry):
    """Remove the backing value immediately before an entry is deleted."""
    if not entry.user_id or entry.asset_value_67 <= 0:
        return
    post_transaction(
        user=entry.user,
        currency=CurrencyTransaction.Currency.SIXTY_SEVEN,
        amount=-entry.asset_value_67,
        reason='HOF asset deleted',
        unique_key=f'hof-delete:{entry.pk}:{entry.asset_revision}',
        hall_entry=None,
        metadata={'entry_id': entry.pk, 'removed_value': entry.asset_value_67},
        allow_negative=True,
    )


def balances_for(user):
    balances = {
        CurrencyTransaction.Currency.SIXTY_ONE: 0,
        CurrencyTransaction.Currency.SIXTY_SEVEN: 0,
    }
    if not getattr(user, 'is_authenticated', False):
        return balances
    for row in CurrencyBalance.objects.filter(user=user):
        balances[row.currency] = row.balance
    return balances


def wealth_rows(currency, limit=67):
    rows = list(
        CurrencyBalance.objects.filter(currency=currency)
        .exclude(balance=0)
        .select_related('user')
        .order_by('-balance', 'user__username')[:limit]
    )
    other_currency = (
        CurrencyTransaction.Currency.SIXTY_ONE
        if currency == CurrencyTransaction.Currency.SIXTY_SEVEN
        else CurrencyTransaction.Currency.SIXTY_SEVEN
    )
    other = {
        row.user_id: row.balance
        for row in CurrencyBalance.objects.filter(user_id__in=[r.user_id for r in rows], currency=other_currency)
    }
    for row in rows:
        row.other_balance = other.get(row.user_id, 0)
    return rows


def _leaderboard_bounds(period, day):
    if period == 'all':
        return None, None
    if period == 'week':
        week_start = day - timedelta(days=day.weekday())
        start, _ = _day_bounds(week_start)
        _, end = _day_bounds(day)
        return start, end
    return _day_bounds(day)


def leaderboard(period='today', game_mode=HallOfFameEntry.GameMode.SIX_SEVEN, day=None, limit=67):
    """Best run per registered user for a period.

    Private runs may compete, as agreed for the daily meta-game, but their video
    remains inaccessible to other users. The leaderboard intentionally exposes
    the score/rank only.
    """
    day = day or timezone.localdate()
    if period not in {'today', 'week', 'all'}:
        period = 'today'
    qs = HallOfFameEntry.objects.filter(user__isnull=False, game_mode=game_mode).select_related('user')
    start, end = _leaderboard_bounds(period, day)
    if start is not None:
        qs = qs.filter(created_at__gte=start, created_at__lt=end)
    qs = qs.order_by('-score', 'created_at', 'id')
    seen = set()
    result = []
    for entry in qs:
        if entry.user_id in seen:
            continue
        seen.add(entry.user_id)
        result.append(entry)
        if len(result) >= limit:
            break
    return result


def _settle_day(day):
    """Settle one completed Melbourne day exactly once."""
    if DailySettlement.objects.filter(date=day).exists():
        return False
    leaders = leaderboard(
        period='today',
        game_mode=HallOfFameEntry.GameMode.SIX_SEVEN,
        day=day,
        limit=len(DAILY_61_PRIZES),
    )
    with transaction.atomic():
        try:
            settlement = DailySettlement.objects.create(date=day)
        except IntegrityError:
            return False
        distributed = 0
        for rank, (entry, prize) in enumerate(zip(leaders, DAILY_61_PRIZES), start=1):
            post_transaction(
                user=entry.user,
                currency=CurrencyTransaction.Currency.SIXTY_ONE,
                amount=prize,
                reason=f'Daily 67 #{rank}',
                unique_key=f'daily61:{day.isoformat()}:{entry.user_id}',
                hall_entry=entry,
                metadata={'date': day.isoformat(), 'rank': rank, 'score': entry.score},
            )
            distributed += prize
        settlement.participant_count = len(leaders)
        settlement.distributed = distributed
        settlement.save(update_fields=['participant_count', 'distributed'])
    return True


def settle_missing_days():
    yesterday = timezone.localdate() - timedelta(days=1)
    latest = DailySettlement.objects.order_by('-date').first()
    # First deployment starts with yesterday; old historical HOFs do not receive
    # retroactive daily prizes. Afterwards every missed date is caught up lazily.
    start = yesterday if latest is None else latest.date + timedelta(days=1)
    day = start
    while day <= yesterday:
        _settle_day(day)
        day += timedelta(days=1)


def owned_cosmetics(user, include_expired=False):
    qs = UserCosmetic.objects.filter(user=user).select_related('cosmetic')
    if include_expired:
        return qs
    now = timezone.now()
    return qs.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))


def purchase_offer(user, offer):
    if not offer.enabled or not offer.cosmetic.enabled:
        raise ValueError('This offer is unavailable.')
    now = timezone.now()
    with transaction.atomic():
        owned = UserCosmetic.objects.select_for_update().filter(user=user, cosmetic=offer.cosmetic).first()
        if owned and owned.expires_at is None:
            raise ValueError('You already own this cosmetic permanently.')

        # A negative balance may exist because HOF backing disappeared, but debt
        # is passive only: purchases can never deepen it.
        post_transaction(
            user=user,
            currency=offer.currency,
            amount=-offer.price,
            reason=f'Bought {offer.cosmetic.name}',
            unique_key=f'purchase:{user.pk}:{offer.pk}:{uuid.uuid4().hex}',
            metadata={
                'cosmetic_id': offer.cosmetic_id,
                'cosmetic': offer.cosmetic.slug,
                'duration_days': offer.duration_days,
            },
            allow_negative=False,
        )
        if owned is None:
            owned = UserCosmetic.objects.create(user=user, cosmetic=offer.cosmetic)
        if offer.duration_days is None:
            owned.expires_at = None
        else:
            owned.expires_at = max(now, owned.expires_at or now) + timedelta(days=offer.duration_days)
        owned.save(update_fields=['expires_at'])
    return owned


def equip_cosmetic(user, cosmetic):
    if not owned_cosmetics(user).filter(cosmetic=cosmetic).exists():
        raise ValueError('You do not currently own this cosmetic.')
    EquippedCosmetic.objects.update_or_create(
        user=user,
        category=cosmetic.category,
        defaults={'cosmetic': cosmetic},
    )


def unequip_cosmetic(user, category):
    if category not in Cosmetic.Category.values:
        raise ValueError('Invalid cosmetic category.')
    EquippedCosmetic.objects.filter(user=user, category=category).delete()


def active_equipped_map(user_ids):
    user_ids = {uid for uid in user_ids if uid}
    if not user_ids:
        return {}
    now = timezone.now()
    valid_pairs = set(
        UserCosmetic.objects.filter(user_id__in=user_ids)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .values_list('user_id', 'cosmetic_id')
    )
    result = {}
    for equipped in EquippedCosmetic.objects.filter(user_id__in=user_ids).select_related('cosmetic'):
        if (equipped.user_id, equipped.cosmetic_id) in valid_pairs:
            result.setdefault(equipped.user_id, {})[equipped.category] = equipped.cosmetic
    return result


def decorate_user_objects(objects, user_attr='user'):
    objects = list(objects)
    user_ids = {
        getattr(getattr(obj, user_attr, None), 'id', None)
        for obj in objects
    }
    equipped = active_equipped_map(user_ids)
    for obj in objects:
        user = getattr(obj, user_attr, None)
        skins = equipped.get(getattr(user, 'id', None), {})
        obj.username_cosmetic = skins.get(Cosmetic.Category.USERNAME)
        obj.badge_cosmetic = skins.get(Cosmetic.Category.BADGE)
        obj.hof_cosmetic = skins.get(Cosmetic.Category.HOF)
        obj.comment_cosmetic = skins.get(Cosmetic.Category.COMMENT)
    return objects


def cosmetic_stylesheet():
    """Render admin-authored cosmetics into scoped CSS selectors.

    Admin CSS is intentionally trusted. Disabled products stay in this sheet so
    existing owners can keep using cosmetics that were later removed from sale.
    """
    blocks = []
    for cosmetic in Cosmetic.objects.all().order_by('id'):
        selector = f'.cosmetic-{cosmetic.pk}'
        if cosmetic.css.strip():
            blocks.append(f'{selector}{{{cosmetic.css}}}')
        if cosmetic.extra_css.strip():
            blocks.append(
                cosmetic.extra_css
                .replace('__SELECTOR__', selector)
                .replace('__IMAGE_URL__', cosmetic.image_url or '')
            )
    return '\n'.join(blocks)
