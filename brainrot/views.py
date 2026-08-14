import json
import math
from datetime import timedelta

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .models import HallOfFameEntry, HallOfFameUploadAttempt
from .validators import validate_hall_of_fame_video


def index(request):
    return render(request, 'brainrot/index.html')


def _counter_context(rival=None):
    context = {
        'turnstile_enabled': settings.TURNSTILE_ENABLED,
        'turnstile_site_key': settings.TURNSTILE_SITE_KEY,
        'max_upload_mb': settings.HOF_MAX_UPLOAD_BYTES // (1024 * 1024),
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
        return (
            response.ok
            and result.get('success') is True
            and result.get('hostname', '').lower() == expected_hostname
        )
    except (requests.RequestException, ValueError):
        return False


@require_POST
@login_required
def submit_hall_of_fame(request):
    recent_cutoff = timezone.now() - timedelta(minutes=1)
    recent_count = HallOfFameUploadAttempt.objects.filter(
        user=request.user,
        created_at__gte=recent_cutoff,
    ).count()
    if recent_count >= settings.HOF_SUBMISSIONS_PER_MINUTE:
        return JsonResponse({'error': 'Rate limit reached. The Institute requests patience.'}, status=429)

    attempt = HallOfFameUploadAttempt.objects.create(user=request.user)

    if not _turnstile_is_valid(request):
        return JsonResponse({'error': 'Human verification failed. Please try again.'}, status=400)

    try:
        score = int(request.POST.get('score', ''))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid score.'}, status=400)
    if score < 0 or score > 500:
        return JsonResponse({'error': 'Score is outside the scientifically plausible range.'}, status=400)

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
            user=request.user,
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
        'message': 'Published to the Hall of Fame. Peer review has been replaced by vibes.',
        'hall_of_fame_url': reverse('brainrot:hall_of_fame'),
        'entry_url': entry_url,
    }, status=201)


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
