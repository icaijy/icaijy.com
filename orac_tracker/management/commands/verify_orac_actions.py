"""Verify fresh GitHub data and the actually deployed live board before removing cron."""
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError

from orac_tracker.baseline import MAX_AGE_HOURS, age_hours, fetch_github_snapshot, fingerprint


class Command(BaseCommand):
    help = 'Verify GitHub snapshots and deployed ORAC integration before disabling the legacy cron.'

    def add_arguments(self, parser):
        parser.add_argument('--site-url', default='https://icaijy.com',
                            help='Deployed website origin (default: https://icaijy.com).')

    def handle(self, *args, **options):
        origin = options['site_url'].rstrip('/')
        parsed = urlsplit(origin)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.query or parsed.fragment or parsed.username:
            raise CommandError('Use an HTTP(S) website origin for --site-url.')
        try:
            snapshot = fetch_github_snapshot()
            age = age_hours(snapshot)
            if not -5 / 60 <= age <= MAX_AGE_HOURS:
                raise ValueError(f'GitHub snapshot age is {age:.1f} hours; expected 0–{MAX_AGE_HOURS}.')
            expected = fingerprint(snapshot)
            self.stdout.write(f'PASS: GitHub snapshot {snapshot["date"]}, captured {snapshot["captured_at"]} ({age:.1f} hours old).')
            response = requests.get(f'{origin}/orac-leaderboards/actions-status/', timeout=(15, 20))
            response.raise_for_status()
            status = response.json()
            if not isinstance(status, dict) or status.get('provider') != 'github-actions' or status.get('legacy_cron_required') is not False:
                raise ValueError('The deployed server has not switched to Actions. Deploy and reload it first.')
            if status.get('ready') is not True or status.get('fingerprint') != expected:
                raise ValueError('The deployed baseline is stale or differs from GitHub. Wait five minutes for cache expiry, then retry.')
            response = requests.get(f'{origin}/orac-leaderboards/', timeout=(15, 60))
            response.raise_for_status()
            board = BeautifulSoup(response.text, 'html.parser').select_one('#orac-leaderboard')
            if board is None or board.get('data-orac-provider') != 'github-actions' or board.get('data-baseline-sha256') != expected or board.get('data-legacy-cron-required') != 'false':
                raise ValueError('The actual leaderboard page does not use the verified GitHub baseline. Check deployment/CDN caching.')
        except (requests.RequestException, ValueError) as exc:
            raise CommandError(f'NOT READY: {exc} Keep the existing cron configuration until this check passes.') from exc
        self.stdout.write(self.style.SUCCESS('PASS: Deployed status and live leaderboard both use the latest GitHub snapshot.'))
        self.stdout.write(self.style.SUCCESS('READY TO DISABLE LEGACY ORAC CRON.'))
        self.stdout.write('Back up `crontab -l`, then use `crontab -e` to comment out only the old ORAC scrape entry. Leave unrelated jobs unchanged.')
        self.stdout.write('Run this check again afterwards. No server cron or auto_data.json is used by the new leaderboard.')
