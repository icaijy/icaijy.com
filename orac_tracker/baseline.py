"""The live board's comparison baseline comes exclusively from Actions snapshots."""
import datetime as dt
import hashlib
import json
import logging
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from django.conf import settings
from django.core.cache import cache

from .history import RAW_BASE, valid_date
from .scraper import validate_payload
from .snapshots import ROOT, TIMEZONE, SOURCE, write_json

logger = logging.getLogger(__name__)
MAX_AGE_HOURS = 36
CACHE_KEY = 'orac-actions-baseline-v1'


def validate_snapshot(value):
    if not isinstance(value, dict) or value.get('schema_version') != 1:
        raise ValueError('Unsupported ORAC snapshot')
    if not valid_date(value.get('date')) or value.get('timezone') != TIMEZONE or value.get('source') != SOURCE:
        raise ValueError('Invalid snapshot date, timezone or source')
    validate_payload(value.get('data'))
    try:
        captured = dt.datetime.fromisoformat(value['captured_at'])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('Invalid capture timestamp') from exc
    if captured.tzinfo is None or captured.astimezone(ZoneInfo(TIMEZONE)).date().isoformat() != value['date']:
        raise ValueError('Capture timestamp does not match snapshot date')
    return value


def fetch_github_snapshot():
    """Fresh network reads only: never let a local fallback pass verification."""
    response = requests.get(f'{RAW_BASE}/index.json', timeout=(15, 15))
    response.raise_for_status()
    index = response.json()
    dates = index.get('dates') if isinstance(index, dict) else None
    if not isinstance(dates, list) or not dates or not all(valid_date(date) for date in dates):
        raise ValueError('GitHub archive has no valid snapshot dates')
    date = max(dates)
    response = requests.get(f'{RAW_BASE}/{date}.json', timeout=(15, 15))
    response.raise_for_status()
    snapshot = validate_snapshot(response.json())
    if snapshot['date'] != date:
        raise ValueError('GitHub index and snapshot date disagree')
    return snapshot


def fingerprint(snapshot):
    encoded = json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def age_hours(snapshot, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    captured = dt.datetime.fromisoformat(snapshot['captured_at'])
    return (now - captured).total_seconds() / 3600


def describe(snapshot, origin):
    age = age_hours(snapshot)
    stale = age > MAX_AGE_HOURS or age < -5 / 60
    return {'snapshot': snapshot, 'origin': origin, 'age_hours': round(age, 2),
            'stale': stale, 'fingerprint': fingerprint(snapshot)}


def get_baseline():
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return describe(cached['snapshot'], cached['origin'])
    saved = Path(getattr(settings, 'ORAC_BASELINE_CACHE_FILE',
                         settings.BASE_DIR / 'orac_tracker' / 'github_baseline.json'))
    try:
        snapshot = fetch_github_snapshot()
        origin = 'github'
        try:
            write_json(saved, snapshot)
        except OSError:
            logger.warning('Could not persist ORAC baseline cache', exc_info=True)
    except (requests.RequestException, ValueError):
        # Keep the most recent validated fallback across process restarts.
        candidates = []
        for path, source in [(saved, 'saved-cache')] + [
            (path, 'checkout') for path in sorted(ROOT.glob('????-??-??.json'), reverse=True)[:1]
        ]:
            try:
                value = validate_snapshot(json.loads(path.read_text(encoding='utf-8')))
                candidates.append((value, source))
            except (OSError, ValueError):
                continue
        if not candidates:
            return {'snapshot': None, 'origin': 'unavailable', 'stale': True, 'fingerprint': ''}
        snapshot, origin = max(candidates, key=lambda item: dt.datetime.fromisoformat(item[0]['captured_at']))
    cache.set(CACHE_KEY, {'snapshot': snapshot, 'origin': origin}, 300)
    return describe(snapshot, origin)
