from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .economy import (
    DAILY_61_PRIZES,
    balances_for,
    cosmetic_stylesheet,
    decorate_user_objects,
    equip_cosmetic,
    leaderboard,
    owned_cosmetics,
    purchase_offer,
    settle_missing_days,
    unequip_cosmetic,
    wealth_rows,
)
from .models import Cosmetic, CosmeticOffer, CurrencyTransaction, EquippedCosmetic, HallOfFameComment, HallOfFameEntry, UserCosmetic


def _settle():
    # No cron: the first visit after midnight settles any completed missing day.
    settle_missing_days()


def _mode(raw):
    return raw if raw in HallOfFameEntry.GameMode.values else HallOfFameEntry.GameMode.SIX_SEVEN


def daily(request):
    _settle()
    game_mode = _mode(request.GET.get('mode'))
    period = request.GET.get('period', 'today')
    if period not in {'today', 'week', 'all'}:
        period = 'today'
    entries = decorate_user_objects(leaderboard(period=period, game_mode=game_mode))
    prizes = DAILY_61_PRIZES if game_mode == HallOfFameEntry.GameMode.SIX_SEVEN and period == 'today' else ()
    for index, entry in enumerate(entries):
        entry.daily_prize = prizes[index] if index < len(prizes) else 0
    return render(request, 'brainrot/daily_leaderboard.html', {
        'entries': entries,
        'game_mode': game_mode,
        'period': period,
        'prizes_enabled': bool(prizes),
    })


def wealth(request):
    _settle()
    currency = request.GET.get('currency', CurrencyTransaction.Currency.SIXTY_SEVEN)
    if currency not in CurrencyTransaction.Currency.values:
        currency = CurrencyTransaction.Currency.SIXTY_SEVEN
    rows = decorate_user_objects(wealth_rows(currency))
    return render(request, 'brainrot/wealth_leaderboard.html', {
        'rows': rows,
        'currency': currency,
        'other_currency': '61' if currency == '67' else '67',
    })


def daily_preview(request):
    """Tiny main-67 Today leaderboard used by the global /67 widget."""
    _settle()
    entries = leaderboard(
        period='today',
        game_mode=HallOfFameEntry.GameMode.SIX_SEVEN,
        limit=5,
    )
    return JsonResponse({
        'entries': [
            {
                'rank': index,
                'name': entry.user.username,
                'score': entry.score,
                'private': entry.visibility == HallOfFameEntry.Visibility.PRIVATE,
            }
            for index, entry in enumerate(entries, start=1)
        ],
        'date': timezone.localdate().isoformat(),
    })


def latest_comments(request):
    """Newest comments across every public HOF specimen."""
    _settle()
    comments = list(
        HallOfFameComment.objects.filter(entry__visibility=HallOfFameEntry.Visibility.PUBLIC)
        .select_related('user', 'entry', 'entry__user')
        .order_by('-created_at', '-id')[:100]
    )
    decorate_user_objects(comments)
    return render(request, 'brainrot/latest_comments.html', {'comments': comments})


def cosmetics_css(request):
    response = HttpResponse(cosmetic_stylesheet(), content_type='text/css; charset=utf-8')
    response['Cache-Control'] = 'public, max-age=30'
    return response


def _shop_cosmetics(user):
    offer_qs = CosmeticOffer.objects.filter(enabled=True).order_by('sort_order', 'price', 'id')
    cosmetics = list(Cosmetic.objects.filter(enabled=True).prefetch_related(Prefetch('offers', queryset=offer_qs)))
    owned_rows = {row.cosmetic_id: row for row in owned_cosmetics(user, include_expired=True)}
    active_ids = set(owned_cosmetics(user).values_list('cosmetic_id', flat=True))
    equipped = {row.category: row.cosmetic_id for row in EquippedCosmetic.objects.filter(user=user)}
    now = timezone.now()
    for cosmetic in cosmetics:
        cosmetic.ownership = owned_rows.get(cosmetic.pk)
        cosmetic.is_active_owned = user.is_superuser or cosmetic.pk in active_ids
        cosmetic.is_equipped = equipped.get(cosmetic.category) == cosmetic.pk
        cosmetic.is_permanent = user.is_superuser or bool(cosmetic.ownership and cosmetic.ownership.expires_at is None)
        cosmetic.is_expired = bool(cosmetic.ownership and cosmetic.ownership.expires_at and cosmetic.ownership.expires_at <= now)
        cosmetic.active_offers = list(cosmetic.offers.all())
    return cosmetics


@login_required
def shop(request):
    _settle()
    category = request.GET.get('category', 'all')
    if category != 'all' and category not in Cosmetic.Category.values:
        category = 'all'
    cosmetics = _shop_cosmetics(request.user)
    if category != 'all':
        cosmetics = [item for item in cosmetics if item.category == category]
    balances = balances_for(request.user)
    return render(request, 'brainrot/shop.html', {
        'cosmetics': cosmetics,
        'category': category,
        'categories': Cosmetic.Category.choices,
        'balance_61': balances['61'],
        'balance_67': balances['67'],
    })


@login_required
def inventory(request):
    _settle()
    rows = list(owned_cosmetics(request.user, include_expired=True).order_by('-acquired_at'))
    active_ids = set(owned_cosmetics(request.user).values_list('cosmetic_id', flat=True))
    equipped = {row.category: row.cosmetic_id for row in EquippedCosmetic.objects.filter(user=request.user)}
    now = timezone.now()
    for row in rows:
        row.is_active = row.cosmetic_id in active_ids
        row.is_equipped = row.is_active and equipped.get(row.cosmetic.category) == row.cosmetic_id
        row.is_expired = bool(row.expires_at and row.expires_at <= now)
    balances = balances_for(request.user)
    return render(request, 'brainrot/inventory.html', {
        'rows': rows,
        'balance_61': balances['61'],
        'balance_67': balances['67'],
    })


@login_required
@require_POST
def buy_cosmetic(request, offer_id):
    offer = get_object_or_404(CosmeticOffer.objects.select_related('cosmetic'), pk=offer_id)
    try:
        purchase_offer(request.user, offer)
        messages.success(request, f'Bought {offer.cosmetic.name}. An outstanding allocation of capital.')
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect(request.POST.get('next') or 'brainrot:shop')


@login_required
@require_POST
def equip(request, cosmetic_id):
    # Disabled cosmetics remain equippable for existing owners.
    cosmetic = get_object_or_404(Cosmetic, pk=cosmetic_id)
    try:
        if request.user.is_superuser:
            # Admin privilege: selecting a skin is free and permanent. No wallet
            # transaction is posted; the ownership row only makes rendering and
            # inventory use the same normal path as everyone else.
            owned, _ = UserCosmetic.objects.get_or_create(user=request.user, cosmetic=cosmetic)
            if owned.expires_at is not None:
                owned.expires_at = None
                owned.save(update_fields=['expires_at'])
        equip_cosmetic(request.user, cosmetic)
        messages.success(request, f'Equipped {cosmetic.name}.')
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect(request.POST.get('next') or 'brainrot:inventory')


@login_required
@require_POST
def unequip(request, category):
    try:
        unequip_cosmetic(request.user, category)
        messages.success(request, 'Cosmetic unequipped.')
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect(request.POST.get('next') or 'brainrot:inventory')
