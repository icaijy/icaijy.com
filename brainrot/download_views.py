from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _

from .models import HallOfFameEntry
from .video_downloads import Mp4TranscodeError, open_compatible_mp4
from .views import hall_of_fame_video as original_hall_of_fame_video


def hall_of_fame_video(request, entry_id):
    """Keep inline/legacy evidence untouched; normalise new downloads to MP4."""
    if request.GET.get('format') != 'mp4':
        return original_hall_of_fame_video(request, entry_id)

    entry = get_object_or_404(HallOfFameEntry.objects.select_related('user'), pk=entry_id)
    may_view = (
        entry.visibility == HallOfFameEntry.Visibility.PUBLIC
        or entry.user_id == request.user.id
        or request.user.is_superuser
    )
    if not may_view:
        return JsonResponse({'error': _('Recording is not public.')}, status=404)

    try:
        handle, size = open_compatible_mp4(entry)
    except Mp4TranscodeError as exc:
        return JsonResponse({'error': str(exc)}, status=503)

    if entry.game_mode == HallOfFameEntry.GameMode.LEG_CLAPS:
        mode_slug = 'tung-tung-leg-claps'
    elif entry.game_mode == HallOfFameEntry.GameMode.VOICE_67:
        mode_slug = 'six-seven-voice'
    else:
        mode_slug = '67'

    response = FileResponse(handle, content_type='video/mp4')
    response['Content-Length'] = size
    response['Content-Disposition'] = f'attachment; filename="{mode_slug}-run-{entry.pk}.mp4"'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response
