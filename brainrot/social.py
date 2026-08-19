import hashlib
import hmac

from django.conf import settings
from django.db.models import Count
from django.utils.encoding import force_bytes

from .models import HallOfFameReaction

REACTION_EMOJIS = tuple(HallOfFameReaction.Emoji.values)


def anonymous_session_key(request, purpose='hof-social', *, create=True):
    """Return a pseudonymous per-browser identity without storing a raw session id."""
    if not request.session.session_key:
        if not create:
            return ''
        request.session.create()
    return hmac.new(
        force_bytes(settings.SECRET_KEY),
        force_bytes(f'{purpose}:{request.session.session_key}'),
        hashlib.sha256,
    ).hexdigest()


def reactor_key(request, *, create=None):
    if request.user.is_authenticated:
        return f'u:{request.user.pk}'
    if create is None:
        create = request.method != 'GET'
    anonymous_key = anonymous_session_key(request, 'hof-reaction', create=create)
    return f'g:{anonymous_key}' if anonymous_key else ''


def reaction_items_map(target_keys, current_reactor_key):
    """Load counts + this viewer's active reactions for many targets in two queries."""
    target_keys = tuple(dict.fromkeys(target_keys))
    if not target_keys:
        return {}

    count_rows = HallOfFameReaction.objects.filter(
        target_key__in=target_keys,
    ).values('target_key', 'emoji').annotate(count=Count('id'))
    counts = {
        (row['target_key'], row['emoji']): row['count']
        for row in count_rows
    }

    active = set()
    if current_reactor_key:
        active = set(HallOfFameReaction.objects.filter(
            target_key__in=target_keys,
            reactor_key=current_reactor_key,
        ).values_list('target_key', 'emoji'))

    return {
        target_key: [
            {
                'emoji': emoji,
                'count': counts.get((target_key, emoji), 0),
                'active': (target_key, emoji) in active,
            }
            for emoji in REACTION_EMOJIS
        ]
        for target_key in target_keys
    }


def reaction_items(target_key, current_reactor_key):
    return reaction_items_map([target_key], current_reactor_key)[target_key]
