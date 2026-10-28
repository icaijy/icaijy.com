"""Read the public GitHub archive, falling back to the deployed checkout."""
import datetime as dt
import json
import re

import requests
from django.core.cache import cache

from .scraper import validate_payload
from .snapshots import ROOT

RAW_BASE = 'https://raw.githubusercontent.com/icaijy/icaijy.com/main/data/orac'
GITHUB_BASE = 'https://github.com/icaijy/icaijy.com/tree/main/data/orac'


def valid_date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return False
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def read_archive(filename):
    key = f'orac-archive:{filename}'
    cached = cache.get(key)
    if cached is not None:
        return cached
    try:
        response = requests.get(f'{RAW_BASE}/{filename}', timeout=(3, 5))
        response.raise_for_status()
        value = response.json()
    except (requests.RequestException, ValueError):
        try:
            value = json.loads((ROOT / filename).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return None
    cache.set(key, value, 300)
    return value


def available_dates():
    index = read_archive('index.json')
    if not isinstance(index, dict) or not isinstance(index.get('dates'), list):
        return []
    return sorted({date for date in index['dates'] if valid_date(date)}, reverse=True)


def load_snapshot(date):
    if not valid_date(date):
        return None
    value = read_archive(f'{date}.json')
    try:
        if value['schema_version'] != 1 or value['date'] != date:
            return None
        validate_payload(value['data'])
        dt.datetime.fromisoformat(value['captured_at'])
    except (KeyError, TypeError, ValueError):
        return None
    return value


def comparison_rows(current, previous):
    rows = []
    for user, count in current.items():
        old = previous.get(user)
        rows.append({'user': user, 'count': count, 'diff': count - old if old is not None else None})
    return rows
