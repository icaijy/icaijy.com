import datetime as dt
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

import requests
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from .history import comparison_rows, load_snapshot, read_archive
from .scraper import parse_leaderboard
from .snapshots import record_snapshot

PAYLOAD = {'overall': {'alice': 10}, 'recent': {'week': {'alice': 2}, 'month': {}, 'year': {'alice': 8}}}


class SnapshotTests(SimpleTestCase):
    def test_melbourne_day_idempotence_and_index(self):
        with tempfile.TemporaryDirectory() as directory:
            fetch = Mock(return_value=PAYLOAD)
            now = dt.datetime(2026, 10, 28, 14, tzinfo=dt.timezone.utc)
            target = record_snapshot(directory, now=now, fetch=fetch)
            self.assertEqual(target.name, '2026-10-29.json')
            content = target.read_bytes()
            record_snapshot(directory, now=now, fetch=fetch)
            fetch.assert_called_once()
            self.assertEqual(target.read_bytes(), content)
            value = json.loads(content)
            self.assertEqual(value['data'], PAYLOAD)
            self.assertEqual(json.loads((Path(directory) / 'index.json').read_text())['dates'], ['2026-10-29'])

    def test_failed_fetch_or_partial_payload_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            for fetch, error in ((Mock(side_effect=requests.Timeout), requests.Timeout), (lambda: {'overall': {}}, ValueError)):
                with self.assertRaises(error):
                    record_snapshot(directory, fetch=fetch)
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_parser_rejects_partial_page_but_accepts_empty_recent_board(self):
        entry = '<li><span class="username-field">alice</span><span class="solvecount">10</span></li>'
        html = f'<div id="overall"><ul class="leaderboard-grid">{entry}</ul></div><div id="recent"><ul><h3>Last Week</h3>{entry}<h3>Last Month</h3><h3>Last Year</h3>{entry}</ul></div>'
        self.assertEqual(parse_leaderboard(html)['recent']['week'], {'alice': 10})
        self.assertEqual(parse_leaderboard(html)['recent']['month'], {})
        with self.assertRaises(ValueError):
            parse_leaderboard(html.replace('<h3>Last Month</h3>', ''))

    def test_new_user_is_unknown_instead_of_zero(self):
        rows = comparison_rows({'alice': 11, 'bob': 20}, {'alice': 10})
        self.assertEqual([row['diff'] for row in rows], [1, None])


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class HistoryTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def snapshot(self, date, count=10):
        return {'schema_version': 1, 'date': date, 'captured_at': f'{date}T12:17:00+00:00',
                'data': {'overall': {'alice': count}, 'recent': PAYLOAD['recent']}}

    @patch('orac_tracker.history.requests.get', side_effect=requests.Timeout)
    def test_network_failure_uses_local_checkout_and_caches(self, get):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'index.json').write_text('{"dates": ["2026-10-28"]}')
            with patch('orac_tracker.history.ROOT', Path(directory)):
                self.assertEqual(read_archive('index.json')['dates'], ['2026-10-28'])
                self.assertEqual(read_archive('index.json')['dates'], ['2026-10-28'])
        get.assert_called_once()

    @patch('orac_tracker.history.read_archive')
    def test_history_compares_previous_available_date_across_gap(self, read):
        values = {'index.json': {'dates': ['2026-10-26', '2026-10-28']},
                  '2026-10-26.json': self.snapshot('2026-10-26', 9),
                  '2026-10-28.json': self.snapshot('2026-10-28', 11)}
        read.side_effect = values.get
        response = self.client.get('/orac-leaderboards/history/')
        self.assertContains(response, '+2')
        self.assertContains(response, '2026-10-26')
        self.assertEqual(response.context['selected'], '2026-10-28')
        self.assertEqual(self.client.get('/orac-leaderboards/history/?date=../../etc/passwd').status_code, 404)

    @patch('orac_tracker.history.read_archive', return_value=None)
    def test_empty_history_is_useful_and_invalid_snapshot_is_safe(self, read):
        self.assertContains(self.client.get('/orac-leaderboards/history/'), 'No snapshots')
        self.assertIsNone(load_snapshot('2026-10-28'))

    @patch('orac_tracker.views.get_baseline')
    def test_live_page_uses_actions_baseline_without_auto_data(self, baseline):
        from . import views
        from .baseline import describe
        snapshot = full_snapshot(count=9)
        baseline.return_value = describe(snapshot, 'github')
        with tempfile.TemporaryDirectory() as directory:
            manual = Path(directory, 'manual.json')
            manual.write_text(json.dumps({'last_updated': 'now', 'data': PAYLOAD}))
            with patch.object(views, 'manual_update', return_value=True), patch.object(views, 'MANUAL_DATA', manual):
                response = self.client.get('/orac-leaderboards/')
            self.assertContains(response, '/orac-leaderboards/history/')
            self.assertContains(response, 'data-orac-provider="github-actions"')
            self.assertEqual(response.context['people']['overall']['alice']['diff'], 1)
            self.assertIsNone(response.context['people']['recent']['week']['alice']['diff'])

    @patch('orac_tracker.views.get_baseline')
    def test_missing_baseline_never_invents_zero(self, baseline):
        from . import views
        baseline.return_value = {'snapshot': None, 'origin': 'unavailable', 'stale': True, 'fingerprint': ''}
        with tempfile.TemporaryDirectory() as directory:
            manual = Path(directory, 'manual.json')
            manual.write_text(json.dumps({'last_updated': 'now', 'data': PAYLOAD}))
            with patch.object(views, 'manual_update', return_value=True), patch.object(views, 'MANUAL_DATA', manual):
                response = self.client.get('/orac-leaderboards/')
            self.assertContains(response, 'Changes are unknown')
            self.assertIsNone(response.context['people']['overall']['alice']['diff'])

    @patch('orac_tracker.views.get_baseline')
    def test_live_failure_displays_snapshot_and_status_uses_same_fingerprint(self, baseline):
        from . import views
        from .baseline import describe
        baseline.return_value = describe(full_snapshot(), 'github')
        with patch.object(views, 'manual_update', return_value=False), patch.object(views, 'MANUAL_DATA', '/nonexistent/orac.json'):
            response = self.client.get('/orac-leaderboards/')
        self.assertContains(response, 'Live refresh is unavailable')
        self.assertEqual(response.context['people']['overall']['alice']['manual'], 9)
        status = self.client.get('/orac-leaderboards/actions-status/').json()
        self.assertFalse(status['legacy_cron_required'])
        self.assertEqual(status['fingerprint'], baseline.return_value['fingerprint'])


def full_snapshot(count=9, now=None):
    from zoneinfo import ZoneInfo
    now = now or dt.datetime.now(dt.timezone.utc)
    return {'schema_version': 1, 'date': now.astimezone(ZoneInfo('Australia/Melbourne')).date().isoformat(),
            'captured_at': now.isoformat(), 'timezone': 'Australia/Melbourne',
            'source': 'https://orac2.info/hub/leaderboards/',
            'data': {'overall': {'alice': count}, 'recent': {'week': {}, 'month': {}, 'year': {}}}}


class BaselineTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @patch('orac_tracker.baseline.fetch_github_snapshot')
    def test_github_baseline_is_cached_and_survives_restart(self, fetch):
        from .baseline import get_baseline
        snapshot = full_snapshot()
        fetch.return_value = snapshot
        with tempfile.TemporaryDirectory() as directory:
            saved = Path(directory, 'github.json')
            with self.settings(ORAC_BASELINE_CACHE_FILE=saved):
                self.assertEqual(get_baseline()['snapshot'], snapshot)
                self.assertEqual(get_baseline()['snapshot'], snapshot)
                fetch.assert_called_once()
                cache.clear()
                fetch.side_effect = requests.Timeout
                with patch('orac_tracker.baseline.ROOT', Path(directory, 'missing')):
                    result = get_baseline()
                self.assertEqual(result['snapshot'], snapshot)
                self.assertEqual(result['origin'], 'saved-cache')

    @patch('orac_tracker.baseline.fetch_github_snapshot', side_effect=requests.Timeout)
    def test_stale_checkout_is_labelled_and_legacy_auto_file_is_ignored(self, fetch):
        from .baseline import get_baseline
        with tempfile.TemporaryDirectory() as directory:
            old = full_snapshot(now=dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=3))
            Path(directory, old['date'] + '.json').write_text(json.dumps(old))
            with self.settings(ORAC_BASELINE_CACHE_FILE=Path(directory, 'missing.json')), patch('orac_tracker.baseline.ROOT', Path(directory)):
                result = get_baseline()
            self.assertTrue(result['stale'])
            self.assertEqual(result['origin'], 'checkout')

    def test_invalid_or_naive_timestamp_is_rejected(self):
        from .baseline import validate_snapshot
        value = full_snapshot()
        value['captured_at'] = '2026-10-28T12:00:00'
        with self.assertRaises(ValueError):
            validate_snapshot(value)

    @patch('orac_tracker.baseline.requests.get')
    def test_strict_fetch_checks_index_and_snapshot(self, get):
        from .baseline import fetch_github_snapshot
        snapshot = full_snapshot()
        get.side_effect = [Mock(json=lambda: {'dates': [snapshot['date']]}), Mock(json=lambda: snapshot)]
        self.assertEqual(fetch_github_snapshot(), snapshot)
        self.assertEqual(get.call_count, 2)


class MigrationVerificationTests(SimpleTestCase):
    def run_check(self, snapshot, responses):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        with patch('orac_tracker.management.commands.verify_orac_actions.fetch_github_snapshot', return_value=snapshot), patch('orac_tracker.management.commands.verify_orac_actions.requests.get', side_effect=responses):
            call_command('verify_orac_actions', stdout=out)
        return out.getvalue()

    def test_checks_deployed_page_before_green_light(self):
        from .baseline import fingerprint
        snapshot = full_snapshot()
        key = fingerprint(snapshot)
        status = Mock(json=lambda: {'provider': 'github-actions', 'legacy_cron_required': False, 'ready': True, 'fingerprint': key})
        page = Mock(text=f'<div id="orac-leaderboard" data-orac-provider="github-actions" data-baseline-sha256="{key}" data-legacy-cron-required="false"></div>')
        self.assertIn('READY TO DISABLE', self.run_check(snapshot, [status, page]))

    def test_stale_data_old_deployment_and_wrong_page_never_pass(self):
        from django.core.management.base import CommandError
        from .baseline import fingerprint
        snapshot = full_snapshot()
        ready = Mock(json=lambda: {'provider': 'github-actions', 'legacy_cron_required': False, 'ready': True, 'fingerprint': fingerprint(snapshot)})
        old = full_snapshot(now=dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=3))
        for value, responses in ((old, []), (snapshot, [Mock(json=lambda: {})]), (snapshot, [ready, Mock(text='<html>old deployment</html>')])):
            with self.subTest(value=value['date'], responses=len(responses)), self.assertRaises(CommandError):
                self.run_check(value, responses)
