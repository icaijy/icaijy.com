from datetime import timedelta
import re

from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.views.decorators.http import require_GET, require_POST
from urllib.parse import urlencode

from .collector import RATE_SUMMARY, enqueue
from .models import Account, Activity, CollectorState, Job, QueryBudget

PATTERNS = {'cf': r'[A-Za-z0-9_.-]{1,24}', 'ac': r'[A-Za-z0-9_]{1,32}'}


def handles_from(request):
    return {platform: request.GET.get(platform, '').strip()[:64] for platform in PATTERNS}


def number(value, default, minimum, maximum):
    try:
        return max(minimum, min(maximum, int(value)))
    except (ValueError, TypeError):
        return default


def build_context(request):
    now = timezone.now()
    cutoff = now - timedelta(days=30)
    platform = request.GET.get('platform', 'cf')
    if platform not in PATTERNS:
        platform = 'cf'
    handles = handles_from(request)
    handle = handles[platform]
    account = Account.objects.filter(platform=platform, handle_key=handle.lower()).first() if handle else None
    pending = bool(handle and (account is None or not account.history_complete))
    mode = request.GET.get('mode', 'all')
    if mode not in ('all', 'solved', 'trying'):
        mode = 'all'
    minimum = number(request.GET.get('min'), 0, 0, 10000)
    min_users = number(request.GET.get('users'), 1, 1, 10000)
    search = request.GET.get('q', '').strip()[:100]
    activities = Activity.objects.filter(account__platform=platform, account__is_peer=True,
                                         last_attempt__gte=cutoff).select_related('account', 'problem')
    if account:
        # All-time AC exclusion, never limited to the peers' 30-day window.
        solved = Activity.objects.filter(account=account, last_ac__isnull=False).values('problem_id')
        activities = activities.exclude(problem_id__in=solved).exclude(account=account)
    if minimum:
        activities = activities.filter(problem__difficulty__gte=minimum)
    if search:
        activities = activities.filter(Q(problem__title__icontains=search) | Q(problem__key__icontains=search))
    groups = {}
    if not pending:
        for activity in activities.iterator():
            problem = activity.problem
            row = groups.setdefault(problem.pk, {'problem': problem, 'users': [], 'solved_count': 0,
                                                  'trying_count': 0, 'latest': activity.last_attempt})
            recent_ac = activity.last_ac is not None and activity.last_ac >= cutoff
            row['users'].append({'account': activity.account, 'recent_ac': recent_ac,
                                 'past_ac': bool(activity.last_ac), 'at': activity.last_attempt})
            row['solved_count'] += int(recent_ac)
            row['trying_count'] += int(not activity.last_ac)
            row['latest'] = max(row['latest'], activity.last_attempt)
    rows = []
    for row in groups.values():
        row['count'] = len(row['users'])
        if row['count'] < min_users or (mode == 'solved' and row['solved_count'] == 0) or (
                mode == 'trying' and row['trying_count'] == 0):
            continue
        row['users'].sort(key=lambda u: (not u['recent_ac'], -(u['account'].rating or 0), u['account'].handle_key))
        rows.append(row)
    rows.sort(key=lambda r: (r['problem'].difficulty is None, -(r['problem'].difficulty or 0), -r['count'], r['problem'].key))
    page = Paginator(rows, 50).get_page(request.GET.get('page'))
    peers = Account.objects.filter(platform=platform, is_peer=True)
    state = CollectorState.objects.filter(pk=1).first()
    backlog = Job.objects.filter(ready_at__lte=now).count()
    return {'rate_summary': RATE_SUMMARY, 'platform': platform, 'handles': handles, 'account': account, 'pending': pending,
            'mode': mode, 'minimum': minimum, 'min_users': min_users, 'search': search,
            'page': page, 'peer_count': peers.count(), 'synced_count': peers.filter(synced_at__isnull=False).count(),
            'fresh_count': peers.filter(synced_at__gte=now - timedelta(hours=36)).count(),
            'oldest_sync': peers.filter(synced_at__isnull=False).order_by('synced_at').values_list('synced_at', flat=True).first(),
            'state': state, 'backlog': backlog, 'collector_stale': not state or not state.last_heartbeat or state.last_heartbeat < now - timedelta(minutes=15),
            'errors': Job.objects.exclude(error='').filter(account__isnull=True).values('kind', 'error'),
            'query_error': request.GET.get('error', '')[:240]}


@require_GET
def index(request):
    context = build_context(request)
    query = request.GET.copy()
    query.pop('page', None)
    query.pop('error', None)
    context['pagination_query'] = query.urlencode()
    for platform in PATTERNS:
        tab_query = query.copy()
        tab_query['platform'] = platform
        context[platform + '_tab_query'] = tab_query.urlencode()
    return render(request, 'holy/index.html', context)


@require_POST
def compare(request):
    handles = {p: request.POST.get(p, '').strip() for p in PATTERNS}
    platform = request.POST.get('platform', 'cf')
    if platform not in PATTERNS:
        platform = 'cf'
    if not handles[platform] and handles['ac' if platform == 'cf' else 'cf']:
        platform = 'ac' if platform == 'cf' else 'cf'
    query = dict(handles, platform=platform)
    for p, handle in handles.items():
        if handle and not re.fullmatch(PATTERNS[p], handle):
            query['error'] = f'Invalid {"Codeforces" if p == "cf" else "AtCoder"} handle.'
            return redirect(reverse('holy:index') + '?' + urlencode(query))
    if not any(handles.values()):
        return redirect('holy:index')
    now = timezone.now()
    # Persistent per-origin-hour budget across WSGI processes. Only trust the
    # socket address; never an arbitrary client-supplied forwarding header.
    identity = request.META.get('REMOTE_ADDR', '') + ':' + now.strftime('%Y-%m-%dT%H')
    key = salted_hmac('holy-query', identity).hexdigest()
    with transaction.atomic():
        budget, _ = QueryBudget.objects.get_or_create(key=key, defaults={'expires_at': now + timedelta(hours=2)})
        admitted = QueryBudget.objects.filter(pk=key, count__lt=20).update(count=F('count') + 1)
        if not admitted or Job.objects.filter(account__isnull=False).count() >= 1000:
            query['error'] = 'Query queue is busy. Please use cached results and try again later.'
        else:
            for p, handle in handles.items():
                if not handle:
                    continue
                account, _ = Account.objects.get_or_create(platform=p, handle_key=handle.lower(), defaults={'handle': handle})
                Account.objects.filter(pk=account.pk).update(comparison_requested=now)
                if not account.history_complete or not account.synced_at or account.synced_at < now - timedelta(hours=6):
                    enqueue(f'user:{account.pk}', 'submissions', account=account, priority=1, now=now)
    return redirect(reverse('holy:index') + '?' + urlencode(query))


@require_GET
def status(request):
    # Read-only polling; does not admit new handles or schedule upstream requests.
    handles = handles_from(request)
    accounts = {}
    for p, handle in handles.items():
        account = Account.objects.filter(platform=p, handle_key=handle.lower()).first() if handle else None
        if account:
            job = Job.objects.filter(account=account).first()
            accounts[p] = {'complete': account.history_complete,
                           'synced_at': account.synced_at.isoformat() if account.synced_at else None,
                           'error': account.error, 'queued': job is not None,
                           'next_try': job.ready_at.isoformat() if job else None}
        else:
            accounts[p] = None
    state = CollectorState.objects.filter(pk=1).first()
    return JsonResponse({'accounts': accounts, 'last_finished': state.last_finished.isoformat() if state and state.last_finished else None,
                         'backlog': Job.objects.filter(ready_at__lte=timezone.now()).count()})
