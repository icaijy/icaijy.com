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
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .models import HallOfFameEntry, HallOfFameUploadAttempt
from .validators import validate_hall_of_fame_video


TURNSTILE_TEST_SECRETS = {
    '1x0000000000000000000000000000000AA',
    '2x0000000000000000000000000000000AA',
    '3x0000000000000000000000000000000AA',
}


def index(request):
    return render(request, 'brainrot/index.html')


def _counter_context(rival=None):
    context = {
        'turnstile_enabled': settings.TURNSTILE_ENABLED,
        'turnstile_site_key': settings.TURNSTILE_SITE_KEY,
        'max_upload_mb': settings.HOF_MAX_UPLOAD_BYTES // (1024 * 1024),
        'anonymous_submission_available': settings.TURNSTILE_ENABLED or settings.DEBUG,
        'rival': rival,
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
    return render(request, 'brainrot/counter.html', _counter_context())


def typing_test(request):
    return render(request, 'brainrot/typing.html')


def hall_of_fame(request):
    entries = HallOfFameEntry.objects.filter(
        state=HallOfFameEntry.State.APPROVED,
    ).select_related('user')[:67]
    return render(request, 'brainrot/hall_of_fame.html', {'entries': entries})


@login_required
def my_hall_of_fame(request):
    entries = HallOfFameEntry.objects.filter(user=request.user)[:67]
    return render(request, 'brainrot/my_hall_of_fame.html', {'entries': entries})


def _public_hall_entry(entry_id):
    return get_object_or_404(
        HallOfFameEntry.objects.select_related('user'),
        pk=entry_id,
        state=HallOfFameEntry.State.APPROVED,
    )


def hall_of_fame_detail(request, entry_id):
    return render(request, 'brainrot/hall_of_fame_detail.html', {
        'entry': _public_hall_entry(entry_id),
    })


@ensure_csrf_cookie
def challenge(request, entry_id):
    return render(request, 'brainrot/counter.html', _counter_context(_public_hall_entry(entry_id)))


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
        # Cloudflare's official test secrets deliberately report localhost even
        # when their dummy widget is embedded on another development host. Real
        # secrets must still match the actual request hostname.
        hostname_matches = (
            settings.TURNSTILE_SECRET_KEY in TURNSTILE_TEST_SECRETS
            or result.get('hostname', '').lower() == expected_hostname
        )
        return response.ok and result.get('success') is True and hostname_matches
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
    name = unicodedata.normalize('NFKC', ' '.join((raw_name or '').strip().split()))
    if not name:
        return 'Anonymous Swan'
    if len(name) > 32:
        raise ValidationError('Display name must be 32 characters or fewer.')
    if any(unicodedata.category(character).startswith('C') for character in name):
        raise ValidationError('Display name contains an unsupported character.')
    if get_user_model().objects.filter(username__iexact=name).exists():
        raise ValidationError('That name belongs to a registered user. Choose a different anonymous display name.')
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

    try:
        score = int(request.POST.get('score', ''))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid score.'}, status=400)
    if score < 0 or score > 500:
        return JsonResponse({'error': 'Score is outside the scientifically plausible range.'}, status=400)

    try:
        display_name = '' if owner else _anonymous_display_name(request.POST.get('display_name', ''))
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
            score=score,
            mime_type=inspected.mime_type,
            duration_seconds=inspected.duration_seconds,
            event_timeline=event_timeline,
            state=HallOfFameEntry.State.APPROVED,
            reviewed_at=timezone.now(),
        )
        entry._validated_extension = inspected.extension
        entry.video = upload
        entry.save()
        attempt.accepted = True
        attempt.save(update_fields=['accepted'])

    entry_url = reverse('brainrot:hall_of_fame_detail', args=(entry.pk,))
    return JsonResponse({
        'ok': True,
        'message': (
            'Published to the Hall of Fame. You can manage it from My HOF.'
            if owner
            else 'Published anonymously. Save the public link; contact the site owner with that link if you need it removed later.'
        ),
        'hall_of_fame_url': reverse('brainrot:hall_of_fame'),
        'entry_url': entry_url,
    }, status=201)


@require_POST
@login_required
def delete_hall_of_fame_entry(request, entry_id):
    entry = get_object_or_404(HallOfFameEntry, pk=entry_id, user=request.user)
    entry.delete()
    return redirect(f"{reverse('brainrot:my_hall_of_fame')}?deleted=1")


def hall_of_fame_video(request, entry_id):
    entry = get_object_or_404(HallOfFameEntry.objects.select_related('user'), pk=entry_id)
    may_view = (
        entry.state == HallOfFameEntry.State.APPROVED
        or entry.user_id == request.user.id
        or request.user.is_staff
    )
    if not may_view:
        return JsonResponse({'error': 'Recording is not public.'}, status=404)

    response = FileResponse(entry.video.open('rb'), content_type=entry.mime_type)
    response['Content-Length'] = entry.video.size
    disposition = 'attachment' if request.GET.get('download') == '1' else 'inline'
    response['Content-Disposition'] = f'{disposition}; filename="67-run-{entry.pk}.{entry.video.name.rsplit(".", 1)[-1]}"'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, max-age=300'
    return response