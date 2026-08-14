from datetime import timedelta

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .models import HallOfFameEntry, HallOfFameUploadAttempt
from .validators import validate_hall_of_fame_video


def index(request):
    return render(request, 'brainrot/index.html')


@ensure_csrf_cookie
def counter(request):
    return render(request, 'brainrot/counter.html', {
        'turnstile_enabled': settings.TURNSTILE_ENABLED,
        'turnstile_site_key': settings.TURNSTILE_SITE_KEY,
        'max_upload_mb': settings.HOF_MAX_UPLOAD_BYTES // (1024 * 1024),
    })


def typing_test(request):
    return render(request, 'brainrot/typing.html')


def hall_of_fame(request):
    entries = HallOfFameEntry.objects.filter(
        state=HallOfFameEntry.State.APPROVED,
    ).select_related('user')[:67]
    own_pending = []
    if request.user.is_authenticated:
        own_pending = HallOfFameEntry.objects.filter(
            user=request.user,
            state=HallOfFameEntry.State.PENDING,
        ).order_by('-created_at')[:5]
    return render(request, 'brainrot/hall_of_fame.html', {
        'entries': entries,
        'own_pending': own_pending,
    })


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
    recent_cutoff = timezone.now() - timedelta(hours=1)
    recent_count = HallOfFameUploadAttempt.objects.filter(
        user=request.user,
        created_at__gte=recent_cutoff,
    ).count()
    if recent_count >= settings.HOF_SUBMISSIONS_PER_HOUR:
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
        )
        entry._validated_extension = inspected.extension
        entry.video = upload
        entry.save()
        attempt.accepted = True
        attempt.save(update_fields=['accepted'])

    return JsonResponse({
        'ok': True,
        'message': 'Submitted for human review. Peer review has never been this important.',
        'hall_of_fame_url': '/brainrot/67/hall-of-fame/',
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
    response['Content-Disposition'] = f'inline; filename="67-run-{entry.pk}.{entry.video.name.rsplit(".", 1)[-1]}"'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, max-age=300'
    return response
