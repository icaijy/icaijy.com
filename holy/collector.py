"""Restart-safe, fair, one-request jobs. Never called from a web request."""
from datetime import datetime, timedelta, timezone as dt_timezone
import fcntl
import re
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from . import upstream
from .models import Account, Activity, CollectorState, Job, Problem, QueryBudget

INTERVAL = 180  # Shared across CF, AtCoder, and AtCoder Problems, including failures.
DAY = timedelta(days=1)


def enqueue(key, kind, *, account=None, payload=None, priority=0, now=None):
    job, _ = Job.objects.get_or_create(key=key, defaults={
        'kind': kind, 'account': account, 'payload': payload or {},
        'priority': priority, 'ready_at': now or timezone.now()})
    if job.priority < priority:
        Job.objects.filter(pk=job.pk).update(priority=priority)
    return job


def schedule(now=None):
    now = now or timezone.now()
    state, _ = CollectorState.objects.get_or_create(pk=1, defaults={
        'next_request_at': now, 'lease_until': now})
    if state.maintenance_at and state.maintenance_at > now - timedelta(minutes=1):
        return
    for kind in ('cf_roster', 'ac_roster', 'cf_problems', 'ac_problems', 'ac_models'):
        enqueue(kind, kind, now=now)
    for account in Account.objects.filter(Q(is_peer=True) | Q(comparison_requested__gte=now - timedelta(days=7))):
        full_needed = account.comparison_requested and not account.history_complete
        if full_needed or not account.synced_at or account.synced_at < now - DAY:
            enqueue(f'user:{account.pk}', 'submissions', account=account,
                    priority=1 if account.comparison_requested else 0, now=now)
    Job.objects.filter(account__is_peer=False, account__comparison_requested__lt=now - timedelta(days=7)).delete()
    QueryBudget.objects.filter(expires_at__lt=now).delete()
    # Keep all ACs for lifetime exclusion, but discard old failed-only records.
    Activity.objects.filter(last_ac__isnull=True, last_attempt__lt=now - timedelta(days=35)).delete()
    CollectorState.objects.filter(pk=1).update(maintenance_at=now)


def update_roster(platform, users, stamp, *, final=True):
    for handle, rating in users:
        Account.objects.update_or_create(platform=platform, handle_key=handle.lower(), defaults={
            'handle': handle, 'rating': rating, 'is_peer': True, 'verified': True, 'roster_seen': stamp})
    if final:
        Account.objects.filter(platform=platform, is_peer=True).filter(
            Q(roster_seen__lt=stamp) | Q(roster_seen__isnull=True)).update(is_peer=False)


def save_activity(account, problem, second, accepted):
    at = datetime.fromtimestamp(int(second), tz=dt_timezone.utc)
    activity, created = Activity.objects.get_or_create(account=account, problem=problem,
        defaults={'last_attempt': at, 'last_ac': at if accepted else None})
    if not created:
        changes = {}
        if at > activity.last_attempt:
            changes['last_attempt'] = at
        if accepted and (activity.last_ac is None or at > activity.last_ac):
            changes['last_ac'] = at
        if changes:
            Activity.objects.filter(pk=activity.pk).update(**changes)


def cf_problem(data):
    contest = int(data['contestId'])
    index = str(data['index'])
    if contest <= 0 or not index.isalnum():
        raise ValueError('Invalid Codeforces problem identity')
    defaults = {'contest': str(contest), 'title': data.get('name', f'{contest}{index}')[:300]}
    if 'rating' in data:
        defaults['difficulty'] = data['rating']
    if 'tags' in data:
        defaults['tags'] = data['tags']
    return Problem.objects.update_or_create(platform='cf', key=f'{contest}/{index}', defaults=defaults)[0]


def submissions(job, now):
    account = job.account
    data = job.payload
    if account.platform == 'ac' and not account.verified:
        upstream.ac_verify(account.handle)
        Account.objects.filter(pk=account.pk).update(verified=True, error='')
        return {}  # Persist verification; submissions get their own rate-limited slot.
    if not data:
        full = bool(account.comparison_requested and not account.history_complete)
        # Overlap by a day to pick up rejudged/pending submissions on subsequent passes.
        since = max(0, account.latest_second - 86400) if account.synced_at else int((now - timedelta(days=30)).timestamp())
        data = {'full': full, 'since': 0 if full else since, 'offset': 1,
                'cursor': 0 if full else since, 'latest': account.latest_second}
    full, since = data['full'], data['since']
    if account.platform == 'cf':
        rows = upstream.cf_api('user.status', handle=account.handle, **{'from': data['offset'], 'count': 1000})
        if not isinstance(rows, list):
            raise ValueError('Invalid CF submissions response')
        for row in rows:
            second = int(row['creationTimeSeconds'])
            data['latest'] = max(data['latest'], second)
            if second >= since and 'contestId' in row['problem']:
                save_activity(account, cf_problem(row['problem']), second, row.get('verdict') == 'OK')
        done = len(rows) < 1000 or (not full and min((r['creationTimeSeconds'] for r in rows), default=0) < since)
        data['offset'] += len(rows)
    else:
        rows = upstream.ac_submissions(account.handle, data['cursor'])
        for row in rows:
            second = int(row['epoch_second'])
            if second < data['cursor']:
                raise ValueError('AtCoder submission cursor moved backwards')
            data['latest'] = max(data['latest'], second)
            key, contest = row['problem_id'], row['contest_id']
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', key) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', contest):
                raise ValueError('Invalid AtCoder problem identity')
            problem, _ = Problem.objects.get_or_create(platform='ac', key=key,
                defaults={'contest': contest, 'title': key})
            save_activity(account, problem, second, row['result'] == 'AC')
        done = len(rows) < 500
        if not done:
            # Inclusive cursor keeps every submission at the page boundary second.
            cursor = max(r['epoch_second'] for r in rows)
            if cursor <= data['cursor']:
                raise ValueError('500+ AtCoder submissions in one second; history remains incomplete')
            data['cursor'] = cursor
    if done:
        changes = {'synced_at': now, 'verified': True, 'error': '', 'latest_second': data['latest']}
        if full:
            changes['history_complete'] = True
        Account.objects.filter(pk=account.pk).update(**changes)
        return None
    return data


def execute(job, now):
    """Return next-page payload, or None when the request completes the job."""
    if job.kind == 'submissions':
        return submissions(job, now)
    if job.kind == 'cf_roster':
        users = upstream.cf_roster()
        with transaction.atomic():
            update_roster('cf', users, now)
    elif job.kind == 'ac_roster':
        page = job.payload.get('page', 1)
        stamp = datetime.fromisoformat(job.payload['stamp']) if job.payload else now
        users, more = upstream.ac_roster(page)
        with transaction.atomic():
            update_roster('ac', users, stamp, final=not more)
        if more:
            if page >= 100:
                raise ValueError('Unexpected AtCoder ranking page count')
            return {'page': page + 1, 'stamp': stamp.isoformat()}
    elif job.kind == 'cf_problems':
        value = upstream.cf_api('problemset.problems')
        if not value.get('problems'):
            raise ValueError('Empty Codeforces problem catalog')
        problems = []
        for row in value['problems']:
            contest, index = int(row['contestId']), str(row['index'])
            if contest <= 0 or not index.isalnum():
                raise ValueError('Invalid Codeforces problem identity')
            problems.append(Problem(platform='cf', key=f'{contest}/{index}', contest=str(contest),
                title=row['name'][:300], difficulty=row.get('rating'), tags=row.get('tags', [])))
        Problem.objects.bulk_create(problems, batch_size=400, update_conflicts=True,
            unique_fields=['platform', 'key'], update_fields=['contest', 'title', 'difficulty', 'tags'])
    elif job.kind == 'ac_problems':
        rows = upstream.ac_resource('problems')
        if not isinstance(rows, list) or not rows:
            raise ValueError('Empty AtCoder problem catalog')
        problems = [Problem(platform='ac', key=row['id'], contest=row['contest_id'], title=row['title'][:300]) for row in rows]
        Problem.objects.bulk_create(problems, batch_size=400, update_conflicts=True,
            unique_fields=['platform', 'key'], update_fields=['contest', 'title'])
    elif job.kind == 'ac_models':
        models = upstream.ac_resource('problem-models')
        if not isinstance(models, dict) or not models:
            raise ValueError('Empty AtCoder difficulty models')
        problems = list(Problem.objects.filter(platform='ac').only('pk', 'key', 'difficulty'))
        changed = []
        for problem in problems:
            value = models.get(problem.key, {}).get('difficulty')
            if value is not None:
                problem.difficulty = upstream.display_difficulty(value)
                changed.append(problem)
        Problem.objects.bulk_update(changed, ['difficulty'], batch_size=400)
    else:
        raise ValueError('Unknown collector job')
    return None


def run_one(now=None):
    # flock also covers a slow streaming roster request beyond the DB lease.
    # No in-process scheduler/threads in WSGI, no long DB transaction over HTTP.
    lock_path = Path(settings.BASE_DIR) / 'holy-collector.lock'
    with lock_path.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 'Another collector is running'
        return _run_locked(now)


def _run_locked(now=None):
    now = now or timezone.now()
    schedule(now)
    CollectorState.objects.filter(pk=1).filter(
        Q(last_heartbeat__isnull=True) | Q(last_heartbeat__lt=now - timedelta(seconds=30))).update(last_heartbeat=now)
    job = Job.objects.filter(ready_at__lte=now).select_related('account').order_by('-priority', 'ready_at', 'pk').first()
    if job is None:
        return 'Queue idle'
    claimed = CollectorState.objects.filter(pk=1, next_request_at__lte=now, lease_until__lte=now).update(
        next_request_at=now + timedelta(seconds=INTERVAL), lease_until=now + timedelta(minutes=15), last_started=now)
    if not claimed:
        return 'Waiting for shared 180-second request budget'
    try:
        result = execute(job, now)
    except Exception as exc:
        # Failed requests consume their slot; retain the last successful cache.
        message = str(exc)[:240] or type(exc).__name__
        delay = max(INTERVAL * 2 ** min(job.failures + 1, 8), getattr(exc, 'retry_after', 0))
        finished = timezone.now()
        Job.objects.filter(pk=job.pk).update(failures=F('failures') + 1, error=message,
            ready_at=finished + timedelta(seconds=delay))
        if job.account_id:
            Account.objects.filter(pk=job.account_id).update(error=message)
        CollectorState.objects.filter(pk=1).update(lease_until=finished, last_finished=finished,
            next_request_at=finished + timedelta(seconds=max(INTERVAL, getattr(exc, 'retry_after', 0))), error=message)
        return f'{job.key}: retry later ({message})'
    finished = timezone.now()
    if job.account_id and result is None:
        job.delete()
    else:
        # Requeue pages at the tail of their priority class, so backfills rotate.
        Job.objects.filter(pk=job.pk).update(payload=result or {}, error='', failures=0,
            ready_at=finished + (timedelta(seconds=1) if result is not None else DAY))
    CollectorState.objects.filter(pk=1).update(lease_until=finished, last_finished=finished,
        last_success=finished, next_request_at=finished + timedelta(seconds=INTERVAL), error='')
    return f'{job.key}: ' + ('next page queued' if result is not None else 'updated')
