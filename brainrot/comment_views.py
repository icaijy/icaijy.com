import hashlib
import hmac
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.views.decorators.http import require_POST

from .comment_markup import comment_max_length, normalise_comment_body, render_comment_markdown
from .models import HallOfFameComment, HallOfFameEntry
from .views import _anonymous_display_name, _may_manage_entry

ANONYMOUS_COMMENT_LIMIT = 3
AUTHENTICATED_COMMENT_LIMIT = 20
COMMENT_RATE_WINDOW = timedelta(minutes=10)


def _entry_is_visible_to(entry, user):
    return entry.visibility == HallOfFameEntry.Visibility.PUBLIC or _may_manage_entry(user, entry)


def _anonymous_comment_key(request):
    """Stable per-browser anonymous key without persisting a raw network address.

    School Wi-Fi can put many real users behind one public IP, so using the HOF
    upload network key here would make one student's three comments exhaust the
    quota for everybody. Django's anonymous session cookie gives each browser a
    separate small quota; the stored value is an HMAC, not the session ID itself.
    """
    if not request.session.session_key:
        request.session.create()
    return hmac.new(
        force_bytes(settings.SECRET_KEY),
        force_bytes(f'hof-comment:{request.session.session_key}'),
        hashlib.sha256,
    ).hexdigest()


def _rate_limit_state(request):
    cutoff = timezone.now() - COMMENT_RATE_WINDOW
    if request.user.is_authenticated:
        recent = HallOfFameComment.objects.filter(
            user=request.user,
            created_at__gte=cutoff,
        ).count()
        return recent, AUTHENTICATED_COMMENT_LIMIT, ''

    client_key = _anonymous_comment_key(request)
    recent = HallOfFameComment.objects.filter(
        user__isnull=True,
        client_key=client_key,
        created_at__gte=cutoff,
    ).count()
    return recent, ANONYMOUS_COMMENT_LIMIT, client_key


@require_POST
def add_comment(request, entry_id):
    entry = get_object_or_404(HallOfFameEntry.objects.select_related('user'), pk=entry_id)
    if not _entry_is_visible_to(entry, request.user):
        return JsonResponse({'error': 'This Hall of Fame entry is private.'}, status=404)

    try:
        body = normalise_comment_body(request.POST.get('body'), request.user)
    except ValidationError as exc:
        return JsonResponse({'error': exc.messages[0]}, status=400)

    recent, limit, client_key = _rate_limit_state(request)
    if recent >= limit:
        return JsonResponse({
            'error': f'Comment rate limit reached. Try again later ({limit} comments per 10 minutes).',
        }, status=429)

    if request.user.is_authenticated:
        user = request.user
        author_name = request.user.username[:32]
    else:
        user = None
        try:
            author_name = _anonymous_display_name(request.POST.get('display_name', ''))
        except ValidationError as exc:
            return JsonResponse({'error': exc.messages[0]}, status=400)

    comment = HallOfFameComment.objects.create(
        entry=entry,
        user=user,
        author_name=author_name,
        body=body,
        client_key=client_key,
    )
    detail_url = reverse('brainrot:hall_of_fame_detail', args=(entry.pk,))
    target = f'{detail_url}?commented=1#comment-{comment.pk}'

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'ok': True,
            'comment_id': comment.pk,
            'url': target,
        }, status=201)
    return redirect(target)


@require_POST
def preview_comment(request):
    raw_body = request.POST.get('body', '')
    if not raw_body.strip():
        return JsonResponse({'html': '<p class="text-secondary mb-0">Nothing to preview yet.</p>'})

    try:
        body = normalise_comment_body(raw_body, request.user)
    except ValidationError as exc:
        return JsonResponse({'error': exc.messages[0]}, status=400)

    return JsonResponse({
        'html': str(render_comment_markdown(body)),
        'max_length': comment_max_length(request.user),
    })


@require_POST
def delete_comment(request, comment_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Log in to manage comments.'}, status=403)

    comment = get_object_or_404(
        HallOfFameComment.objects.select_related('entry', 'entry__user'),
        pk=comment_id,
    )
    may_delete = (
        request.user.is_superuser
        or comment.user_id == request.user.id
        or comment.entry.user_id == request.user.id
    )
    if not may_delete:
        return JsonResponse({'error': 'You cannot delete this comment.'}, status=404)

    entry_id = comment.entry_id
    comment.delete()
    return redirect(f'{reverse("brainrot:hall_of_fame_detail", args=(entry_id,))}#comments')
