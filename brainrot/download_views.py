from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _

from .models import HallOfFameEntry


def hall_of_fame_video(request, entry_id):
    """Stream the validated stored recording directly without server transcoding."""
    entry = get_object_or_404(HallOfFameEntry.objects.select_related('user'), pk=entry_id)
    may_view = (
        entry.visibility == HallOfFameEntry.Visibility.PUBLIC
        or entry.user_id == request.user.id
        or request.user.is_superuser
    )
    if not may_view:
        return JsonResponse({'error': _('Recording is not public.')}, status=404)

    extension = entry.video.name.rsplit('.', 1)[-1].lower() if '.' in entry.video.name else 'mp4'
    if entry.game_mode == HallOfFameEntry.GameMode.LEG_CLAPS:
        mode_slug = 'tung-tung-leg-claps'
    elif entry.game_mode == HallOfFameEntry.GameMode.VOICE_67:
        mode_slug = 'six-seven-voice'
    else:
        mode_slug = '67'

    response = FileResponse(entry.video.open('rb'), content_type=entry.mime_type)
    response['Content-Length'] = entry.video.size
    disposition = 'attachment' if request.GET.get('download') == '1' else 'inline'
    response['Content-Disposition'] = (
        f'{disposition}; filename="{mode_slug}-run-{entry.pk}.{extension}"'
    )
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, max-age=300'
    return response
