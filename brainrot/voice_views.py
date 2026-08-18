from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import HallOfFameEntry


@ensure_csrf_cookie
def voice_counter(request):
    rival = None
    rival_id = request.GET.get('rival')
    if rival_id:
        rival = get_object_or_404(
            HallOfFameEntry.objects.select_related('user'),
            pk=rival_id,
            game_mode=HallOfFameEntry.GameMode.VOICE_67,
            visibility=HallOfFameEntry.Visibility.PUBLIC,
        )

    context = {
        'turnstile_enabled': settings.TURNSTILE_ENABLED,
        'turnstile_site_key': settings.TURNSTILE_SITE_KEY,
        'max_upload_mb': settings.HOF_MAX_UPLOAD_BYTES // (1024 * 1024),
        'anonymous_submission_available': settings.TURNSTILE_ENABLED or settings.DEBUG,
        'rival': rival,
        'game_mode': HallOfFameEntry.GameMode.VOICE_67,
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

    return render(request, 'brainrot/voice_counter.html', context)


def challenge_dispatch(request, entry_id):
    rival = get_object_or_404(
        HallOfFameEntry.objects.only('id', 'game_mode', 'visibility'),
        pk=entry_id,
        visibility=HallOfFameEntry.Visibility.PUBLIC,
    )
    if rival.game_mode == HallOfFameEntry.GameMode.VOICE_67:
        return redirect(f"{reverse('brainrot:voice_counter')}?rival={rival.pk}")

    # Keep the mature pose challenge path exactly as-is for the two camera modes.
    from . import views
    return views.challenge(request, entry_id)
