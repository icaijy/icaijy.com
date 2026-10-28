import json
import os

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect

from .baseline import get_baseline
from .scraper import validate_payload

MANUAL_DATA = os.path.join(settings.BASE_DIR, 'orac_tracker', 'manual_data.json')


def manual_update(request=None):
    # The current board still refreshes on visits; only scheduled collection moved.
    from . import scraper
    updated = scraper.main('manual')
    return redirect('index') if request is not None else updated


def merge_board(current, baseline):
    return {
        user: {'manual': count, 'auto': baseline.get(user),
               'diff': count - baseline[user] if user in baseline else None}
        for user, count in current.items()
    }


def index(request):
    updated = manual_update()
    current = None
    try:
        with open(MANUAL_DATA, encoding='utf-8') as stream:
            current = json.load(stream)
        validate_payload(current['data'])
    except (OSError, ValueError, KeyError, TypeError):
        current = None
    baseline = get_baseline()
    snapshot = baseline['snapshot']
    live_unavailable = not updated or current is None
    # A live fetch outage can display the dated snapshot, with an explicit label.
    if current is None:
        current = {'last_updated': snapshot['captured_at'] if snapshot else None,
                   'data': snapshot['data'] if snapshot else {'overall': {}, 'recent': {}}}
    previous = snapshot['data'] if snapshot else {'overall': {}, 'recent': {}}
    people = {
        'overall': merge_board(current['data']['overall'], previous['overall']),
        'recent': {period: merge_board(current['data']['recent'].get(period, {}),
                                      previous['recent'].get(period, {}))
                   for period in ('week', 'month', 'year')},
    }
    return render(request, 'leaderboard/index.html', {
        'people': people, 'last_updated': current.get('last_updated'),
        'baseline': baseline, 'live_unavailable': live_unavailable,
    })


def actions_status(request):
    baseline = get_baseline()
    snapshot = baseline['snapshot']
    response = JsonResponse({
        'provider': 'github-actions', 'legacy_cron_required': False,
        'ready': snapshot is not None and not baseline['stale'],
        'origin': baseline['origin'], 'stale': baseline['stale'],
        'date': snapshot['date'] if snapshot else None,
        'captured_at': snapshot['captured_at'] if snapshot else None,
        'fingerprint': baseline['fingerprint'],
    })
    response['Cache-Control'] = 'no-store'
    return response


def history(request):
    from .history import available_dates, load_snapshot, comparison_rows, GITHUB_BASE
    dates = available_dates()
    selected = request.GET.get('date') or (dates[0] if dates else None)
    context = {'dates': dates, 'selected': selected, 'github_url': GITHUB_BASE}
    if selected and selected not in dates:
        context['error'] = 'No snapshot is available for that date.'
        return render(request, 'leaderboard/history.html', context, status=404)
    if selected:
        snapshot = load_snapshot(selected)
        if snapshot is None:
            context['error'] = 'This snapshot could not be loaded. Please try again later or browse GitHub.'
        else:
            position = dates.index(selected)
            previous_date = dates[position + 1] if position + 1 < len(dates) else None
            previous = load_snapshot(previous_date) if previous_date else None
            previous_data = previous['data'] if previous else {'overall': {}, 'recent': {}}
            boards = [('Overall', snapshot['data']['overall'], previous_data['overall'])]
            for period in ('week', 'month', 'year'):
                boards.append((period.title(), snapshot['data']['recent'][period], previous_data['recent'].get(period, {})))
            context.update({
                'snapshot': snapshot,
                'previous_date': previous_date if previous else None,
                'boards': [{'title': title, 'rows': comparison_rows(current, old)} for title, current, old in boards],
            })
    return render(request, 'leaderboard/history.html', context)
