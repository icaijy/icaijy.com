import json
import hashlib
import hmac
import math
import unicodedata
from datetime import timedelta

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .comment_markup import comment_max_length, normalise_comment_body
from .models import HallOfFameComment, HallOfFameEntry, HallOfFameUploadAttempt
from .validators import validate_hall_of_fame_video


def index(request):
    return render(request, 'brainrot/index.html')


def _normalise_game_mode(raw_mode):
    if raw_mode in HallOfFameEntry.GameMode.values:
        return raw_mode
    return HallOfFameEntry.GameMode.SIX_SEVEN


def _counter_context(rival=None, game_mode=HallOfFameEntry.GameMode.SIX_SEVEN):
    context = {
        'turnstile_enabled': settings.TURNSTILE_ENABLED,
        'turnstile_site_key': settings.TURNSTILE_SITE_KEY,
        'max_upload_mb': settings.HOF_MAX_UPLOAD_BYTES // (1024 * 1024),
        'anonymous_submission_available': settings.TURNSTILE_ENABLED or settings.DEBUG,
        'rival': rival,
        'game_mode': game_mode,
    }
    if rival is not None:
        timeline = rival.event_timeline
        timeline_exact = len(timeline) == rival.score
        if not timeline_exact and rival.score:
            timeline = [round((index + 1) * 20 / (rival.score + 1), 3) for index in range(rival.score)]
        context.update({
            'rival_timeline': timeline,
            'rival_timeline_exact': timeline_exact,
        })
    return context


@ensure_csrf_cookie
def counter(request):
    game_mode = _normalise_game_mode(request.GET.get('mode'))
    return render(request, 'brainrot/counter.html', _counter_context(game_mode=game_mode))


def typing_test(request):
    return render(request, 'brainrot/typing.html')


def hall_of_fame(request):
    game_mode = _normalise_game_mode(request.GET.get('mode'))
    entries = HallOfFameEntry.objects.filter(
        game_mode=game_mode,
        visibility=HallOfFameEntry.Visibility.PUBLIC,
    ).select_related('user').annotate(comment_count=Count('comments'))[:67]
    return render(request, 'brainrot/hall_of_fame.html', {
        'entries': entries,
        'game_mode': game_mode,
    })


@login_required
def my_hall_of_fame(request):
    entries = HallOfFameEntry.objects.select_related('user')
    if not request.user.is_superuser:
        entries = entries.filter(user=request.user)
    return render(request, 'brainrot/my_hall_of_fame.html', {
        'entries': entries[:67],
        'superuser_mode': request.user.is_superuser,
    })


def _public_hall_entry(entry_id):
    return get_object_or_404(
        HallOfFameEntry.objects.select_related('user'),
        pk=entry_id,
        visibility=HallOfFameEntry.Visibility.PUBLIC,
    )


def hall_of_fame_detail(request, entry_id):
    entry = get_object_or_404(HallOfFameEntry.objects.select_related('user'), pk=entry_id)
    if entry.visibility != HallOfFameEntry.Visibility.PUBLIC and not _may_manage_entry(request.user, entry):
        return JsonResponse({'error': _('This Hall of Fame entry is private.')}, status=404)
    comments = entry.comments.select_related('user', 'entry', 'entry__user').all()
    return render(request, 'brainrot/hall_of_fame_detail.html', {
        'entry': entry,
        'comments': comments,
        'comment_max_length': comment_max_length(request.user),
    })


@ensure_csrf_cookie
def challenge(request, entry_id):
    rival = _public_hall_entry(entry_id)
    return render(request, 'brainrot/counter.html', _counter_context(rival, rival.game_mode))


def _validated_event_timeline(raw_timeline, score):
    if not raw_timeline:
        return []
    try:
        timeline = json.loads(raw_timeline)
    except (TypeError, json.JSONDecodeError):
        raise ValidationError('The counter timeline is not valid JSON.')
    if not isinstance(timeline, list) or len(timeline) != score or len(timeline) > 500:
        raise ValidationError('The counter timeline does not match the submitted score.')

    cleaned = []
    for value in timeline:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValidationError('The counter timeline contains an invalid timestamp.')
        timestamp = round(float(value), 3)
        if timestamp < 0 or timestamp > 20.5 or (cleaned and timestamp < cleaned[-1]):
            raise ValidationError('The counter timeline contains an invalid timestamp.')
        cleaned.append(timestamp)
    return cleaned


def _turnstile_is_valid(request):
    if not settings.TURNSTILE_ENABLED:
        return True
    token = request.POST.get('cf-turnstile-response', '')
    if not token:
        return False
    try:
        response = requests.post(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={
                'secret': settings.TURNSTILE_SECRET_KEY,
                'response': token,
                'remoteip': request.META.get('REMOTE_ADDR', ''),
            },
            timeout=5,
        )
        result = response.json()
        expected_hostname = request.get_host().split(':', 1)[0].lower()
        return (
            response.ok
            and result.get('success') is True
            and result.get('hostname', '').lower() == expected_hostname
        )
    except (requests.RequestException, ValueError):
        return False


def _upload_client_key(request):
    """Pseudonymous network key for anonymous rate limiting; no raw IP is stored."""
    trusted_header = settings.HOF_TRUSTED_IP_HEADER
    address = request.META.get(trusted_header, '') if trusted_header else ''
    if trusted_header and ',' in address:
        address = address.split(',', 1)[0]
    address = address.strip() or request.META.get('REMOTE_ADDR', '') or 'unknown'
    return hmac.new(
        force_bytes(settings.SECRET_KEY),
        force_bytes(f'hof-upload:{address}'),
        hashlib.sha256,
    ).hexdigest()


def _anonymous_display_name(raw_name):
    name = ' '.join((raw_name or '').strip().split())
    if not name:
        return 'Anonymous Swan'
    if len(name) > 32:
        raise ValidationError('Display name must be 32 characters or fewer.')
    if any(unicodedata.category(character).startswith('C') for character in name):
        raise ValidationError('Display name contains an unsupported character.')
    canonical_name = unicodedata.normalize('NFKC', name).casefold()
    reserved_names = {'admin', 'administrator', 'moderator', 'staff', 'owner', 'icaijy'}
    registered_names = {
        unicodedata.normalize('NFKC', username).casefold()
        for username in get_user_model().objects.values_list('username', flat=True)
    }
    if canonical_name in reserved_names or canonical_name in registered_names:
        raise ValidationError('That display name belongs to a registered user or reserved site role.')
    return name


@require_POST
def submit_hall_of_fame(request):
    owner = request.user if request.user.is_authenticated else None
    if owner is None and not (settings.TURNSTILE_ENABLED or settings.DEBUG):
        return JsonResponse({
            'error': 'Anonymous submission is unavailable until Turnstile is configured.',
        }, status=503)

    client_key = _upload_client_key(request)
    recent_cutoff = timezone.now() - timedelta(minutes=1)
    identity_filter = {'user': request.user} if request.user.is_authenticated else {'client_key': client_key}
    recent_count = HallOfFameUploadAttempt.objects.filter(
        created_at__gte=recent_cutoff,
        **identity_filter,
    ).count()
    if recent_count >= settings.HOF_SUBMISSIONS_PER_MINUTE:
        return JsonResponse({'error': 'Rate limit reached. The Institute requests patience.'}, status=429)

    attempt = HallOfFameUploadAttempt.objects.create(user=owner, client_key=client_key)

    if not _turnstile_is_valid(request):
        return JsonResponse({'error': 'Human verification failed. Please try again.'}, status=400)

    if request.POST.get('publication_consent') != 'yes':
        return JsonResponse({
            'error': _('You must confirm that this video will be published for anyone to watch.'),
        }, status=400)

    try:
        score = int(request.POST.get('score', ''))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid score.'}, status=400)
    if score < 0 or score > 500:
        return JsonResponse({'error': 'Score is outside the scientifically plausible range.'}, status=400)

    game_mode = request.POST.get('game_mode') or HallOfFameEntry.GameMode.SIX_SEVEN
    if game_mode not in HallOfFameEntry.GameMode.values:
        return JsonResponse({'error': _('Invalid counter mode.')}, status=400)

    try:
        display_name = '' if owner else _anonymous_display_name(request.POST.get('display_name', ''))
    except ValidationError as exc:
        return JsonResponse({'error': exc.messages[0]}, status=400)

    try:
        submission_comment = normalise_comment_body(
            request.POST.get('submission_comment', ''),
            request.user,
            allow_blank=True,
        )
    except ValidationError as exc:
        return JsonResponse({'error': exc.messages[0]}, status=400)

    try:
        event_timeline = _validated_event_timeline(request.POST.get('event_timeline', ''), score)
    except ValidationError as exc:
        return JsonResponse({'error': exc.messages[0]}, status=400)

    upload = request.FILES.get('video')
    if upload is None:
        return JsonResponse({'error': 'A recording is required for Hall of Fame review.'}, status=400)
    try:
        inspected = validate_hall_of_fame_video(upload)
    except ValidationError as exc:
        return JsonResponse({'error': exc.messages[0]}, status=400)

    with transaction.atomic():
        entry = HallOfFameEntry(
            user=owner,
            display_name=display_name,
            game_mode=game_mode,
            score=score,
            mime_type=inspected.mime_type,
            duration_seconds=inspected.duration_seconds,
            event_timeline=event_timeline,
            visibility=HallOfFameEntry.Visibility.PUBLIC,
        )
        entry._validated_extension = inspected.extension
        entry.video = upload
        entry.save()
        if submission_comment:
            HallOfFameComment.objects.create(
                entry=entry,
                user=owner,
                author_name=owner.username[:32] if owner else display_name,
                body=submission_comment,
                client_key='' if owner else client_key,
                is_submission_note=True,
            )
        attempt.accepted = True
        attempt.save(update_fields=['accepted'])

    entry_url = reverse('brainrot:hall_of_fame_detail', args=(entry.pk,))
    return JsonResponse({
        'ok': True,
        'message': (
            _('Published to the Hall of Fame. You can manage it from My HOF.')
            if owner
            else _('Published as a guest. To remove it later, send the public link to the site owner.')
        ),
        'hall_of_fame_url': reverse('brainrot:hall_of_fame'),
        'entry_url': entry_url,
    }, status=201)


@require_POST
@login_required
def delete_hall_of_fame_entry(request, entry_id):
    entry = get_object_or_404(HallOfFameEntry, pk=entry_id)
    if not _may_manage_entry(request.user, entry):
        return JsonResponse({'error': _('You cannot manage this entry.')}, status=404)
    entry.delete()
    return redirect(_management_redirect(request, deleted=True))


def _may_manage_entry(user, entry):
    return user.is_authenticated and (user.is_superuser or entry.user_id == user.id)


def _management_redirect(request, deleted=False):
    requested = request.POST.get('next', '')
    if requested and url_has_allowed_host_and_scheme(
        requested,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return requested
    suffix = '?deleted=1' if deleted else '?updated=1'
    return f"{reverse('brainrot:my_hall_of_fame')}{suffix}"


@require_POST
@login_required
def set_hall_of_fame_visibility(request, entry_id):
    entry = get_object_or_404(HallOfFameEntry, pk=entry_id)
    if not _may_manage_entry(request.user, entry):
        return JsonResponse({'error': _('You cannot manage this entry.')}, status=404)
    visibility = request.POST.get('visibility')
    if visibility not in HallOfFameEntry.Visibility.values:
        return JsonResponse({'error': _('Invalid visibility.')}, status=400)
    entry.visibility = visibility
    entry.save(update_fields=['visibility'])
    return redirect(_management_redirect(request))


def hall_of_fame_video(request, entry_id):
    entry = get_object_or_404(HallOfFameEntry.objects.select_related('user'), pk=entry_id)
    may_view = (
        entry.visibility == HallOfFameEntry.Visibility.PUBLIC
        or entry.user_id == request.user.id
        or request.user.is_superuser
    )
    if not may_view:
        return JsonResponse({'error': _('Recording is not public.')}, status=404)

    response = FileResponse(entry.video.open('rb'), content_type=entry.mime_type)
    response['Content-Length'] = entry.video.size
    disposition = 'attachment' if request.GET.get('download') == '1' else 'inline'
    mode_slug = 'leg-claps' if entry.game_mode == HallOfFameEntry.GameMode.LEG_CLAPS else '67'
    response['Content-Disposition'] = f'{disposition}; filename="{mode_slug}-run-{entry.pk}.{entry.video.name.rsplit(".", 1)[-1]}"'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, max-age=300'
    return response
