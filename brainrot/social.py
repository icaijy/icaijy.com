import hashlib
import hmac

from django.conf import settings
from django.db.models import Count
from django.utils.encoding import force_bytes

from .models import HallOfFameReaction

REACTION_EMOJIS = tuple(HallOfFameReaction.Emoji.values)


def anonymous_session_key(request, purpose='hof-social'):
    """Return a pseudonymous per-browser identity without storing a raw session id."""
    if not request.session.session_key:
        request.session.create()
    return hmac.new(
        force_bytes(settings.SECRET_KEY),
        force_bytes(f'{purpose}:{request.session.session_key}'),
        hashlib.sha256,
    ).hexdigest()


def reactor_key(request):
    if request.user.is_authenticated:
        return f'u:{request.user.pk}'
    return f'g:{anonymous_session_key(request, "hof-reaction")}'


def reaction_items(target_key, current_reactor_key):
    rows = HallOfFameReaction.objects.filter(target_key=target_key).values('emoji').annotate(count=Count('id'))
    counts = {row['emoji']: row['count'] for row in rows}
    active = set(HallOfFameReaction.objects.filter(
        target_key=target_key,
        reactor_key=current_reactor_key,
    ).values_list('emoji', flat=True))
    return [
        {
            'emoji': emoji,
            'count': counts.get(emoji, 0),
            'active': emoji in active,
        }
        for emoji in REACTION_EMOJIS
    ]
