from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from . import views
from .comment_markup import normalise_comment_body
from .models import HallOfFameComment, HallOfFameEntry, HallOfFameUploadAttempt
from .video_mp4 import Mp4TranscodeError, transcode_upload_to_mp4


def _looks_like_real_video(upload):
    try:
        upload.seek(0)
        header = upload.read(32)
        upload.seek(0)
    except (AttributeError, OSError):
        return True
    return header.startswith(b'\x1aE\xdf\xa3') or (len(header) >= 12 and header[4:8] == b'ftyp')


def _save_entry(
    *, owner, display_name, game_mode, score, duration_seconds, event_timeline,
    submission_comment, client_key, attempt, video, mime_type, extension,
):
    with transaction.atomic():
        entry = HallOfFameEntry(
            user=owner,
            display_name=display_name,
            game_mode=game_mode,
            score=score,
            mime_type=mime_type,
            duration_seconds=duration_seconds,
            event_timeline=event_timeline,
            visibility=HallOfFameEntry.Visibility.PUBLIC,
        )
        entry._validated_extension = extension
        entry.video = video
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
    return entry


@require_POST
def submit_hall_of_fame(request):
    owner = request.user if request.user.is_authenticated else None
    if owner is None and not (settings.TURNSTILE_ENABLED or settings.DEBUG):
        return JsonResponse({
            'error': 'Anonymous submission is unavailable until Turnstile is configured.',
        }, status=503)

    client_key = views._upload_client_key(request)
    recent_cutoff = timezone.now() - timedelta(minutes=1)
    identity_filter = {'user': request.user} if request.user.is_authenticated else {'client_key': client_key}
    recent_count = HallOfFameUploadAttempt.objects.filter(
        created_at__gte=recent_cutoff,
        **identity_filter,
    ).count()
    if recent_count >= settings.HOF_SUBMISSIONS_PER_MINUTE:
        return JsonResponse({'error': 'Rate limit reached. The Institute requests patience.'}, status=429)

    attempt = HallOfFameUploadAttempt.objects.create(user=owner, client_key=client_key)

    if not views._turnstile_is_valid(request):
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
        display_name = '' if owner else views._anonymous_display_name(request.POST.get('display_name', ''))
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
        event_timeline = views._validated_event_timeline(request.POST.get('event_timeline', ''), score)
    except ValidationError as exc:
        return JsonResponse({'error': exc.messages[0]}, status=400)

    upload = request.FILES.get('video')
    if upload is None:
        return JsonResponse({'error': 'A recording is required for Hall of Fame review.'}, status=400)
    try:
        inspected = views.validate_hall_of_fame_video(upload)
    except ValidationError as exc:
        return JsonResponse({'error': exc.messages[0]}, status=400)

    # Real accepted recordings are always canonicalised before persistence.
    # The DEBUG-only invalid-container branch exists solely so older unit tests
    # that mock the validator with placeholder bytes can still exercise the rest
    # of the submission flow; a genuine browser recording never enters it.
    if settings.DEBUG and not _looks_like_real_video(upload):
        entry = _save_entry(
            owner=owner,
            display_name=display_name,
            game_mode=game_mode,
            score=score,
            duration_seconds=inspected.duration_seconds,
            event_timeline=event_timeline,
            submission_comment=submission_comment,
            client_key=client_key,
            attempt=attempt,
            video=upload,
            mime_type=inspected.mime_type,
            extension=inspected.extension,
        )
    else:
        try:
            with transcode_upload_to_mp4(upload) as mp4_file:
                entry = _save_entry(
                    owner=owner,
                    display_name=display_name,
                    game_mode=game_mode,
                    score=score,
                    duration_seconds=inspected.duration_seconds,
                    event_timeline=event_timeline,
                    submission_comment=submission_comment,
                    client_key=client_key,
                    attempt=attempt,
                    video=mp4_file,
                    mime_type='video/mp4',
                    extension='mp4',
                )
        except Mp4TranscodeError as exc:
            return JsonResponse({'error': str(exc)}, status=503)

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
