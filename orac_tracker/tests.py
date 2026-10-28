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

    @patch('orac_tracker.history.requests.get')
    def test_live_page_keeps_server_daily_baseline_and_history_link(self, get):
        from . import views
        with tempfile.TemporaryDirectory() as directory:
            manual, auto = Path(directory, 'manual.json'), Path(directory, 'auto.json')
            manual.write_text(json.dumps({'last_updated': 'now', 'data': PAYLOAD}))
            auto.write_text(json.dumps({'overall': {'alice': 9}, 'recent': PAYLOAD['recent']}))
            with patch.object(views, 'manual_update'), patch.object(views, 'MANUAL_DATA', manual), patch.object(views, 'AUTO_DATA', auto):
                response = self.client.get('/orac-leaderboards/')
            self.assertContains(response, '/orac-leaderboards/history/')
            self.assertEqual(response.context['people']['overall']['alice']['diff'], 1)
        get.assert_not_called()
