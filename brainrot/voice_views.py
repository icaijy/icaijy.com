from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import HallOfFameEntry


def voice_counter(request):
    """Public placeholder while the fast continuous-speech detector is rebuilt."""
    return render(request, 'brainrot/voice_coming_soon.html')


def challenge_dispatch(request, entry_id):
    rival = get_object_or_404(
        HallOfFameEntry.objects.only('id', 'game_mode', 'visibility'),
        pk=entry_id,
        visibility=HallOfFameEntry.Visibility.PUBLIC,
    )
    if rival.game_mode == HallOfFameEntry.GameMode.VOICE_67:
        # Historical Voice HOF links remain valid, but new voice runs are
        # intentionally unavailable until the purpose-built detector ships.
        return redirect(reverse('brainrot:voice_counter'))

    # Keep the mature pose challenge path exactly as-is for the two camera modes.
    from . import views
    return views.challenge(request, entry_id)
