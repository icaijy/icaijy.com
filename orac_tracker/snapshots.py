"""Django-independent daily archive writer; run with python -m orac_tracker.snapshots."""
import argparse
import datetime as dt
import json
import os
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

from .scraper import fetch_leaderboard, validate_payload

ROOT = Path(__file__).resolve().parent.parent / 'data' / 'orac'
TIMEZONE = 'Australia/Melbourne'
SOURCE = 'https://orac2.info/hub/leaderboards/'


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix=path.name + '.', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def record_snapshot(root=ROOT, *, now=None, fetch=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        raise ValueError('Capture time must include a timezone')
    date = now.astimezone(ZoneInfo(TIMEZONE)).date().isoformat()
    root = Path(root)
    target = root / f'{date}.json'
    # First successful capture wins: retries never rewrite a historical day.
    if not target.exists():
        payload = (fetch or fetch_leaderboard)()
        validate_payload(payload)
        write_json(target, {
            'schema_version': 1,
            'date': date,
            'timezone': TIMEZONE,
            'captured_at': now.astimezone(dt.timezone.utc).isoformat(),
            'source': SOURCE,
            'data': payload,
        })
    dates = sorted(p.stem for p in root.glob('????-??-??.json'))
    write_json(root / 'index.json', {
        'schema_version': 1, 'timezone': TIMEZONE, 'dates': dates,
    })
    print(f'Daily snapshot available: {target}')
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT)
    args = parser.parse_args()
    record_snapshot(args.output)


if __name__ == '__main__':
    main()
