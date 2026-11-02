from datetime import timedelta
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import requests
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from .collector import enqueue, execute, run_one, save_activity, schedule, submissions, update_roster
from .models import Account, Activity, CollectorState, Job, Problem, QueryBudget
from .upstream import UpstreamError, cf_roster, display_difficulty, fetch, parse_ac_roster


class UpstreamTests(SimpleTestCase):
    def test_ranking_reads_current_rating_and_all_pages(self):
        html = '''<table><tbody><tr><td>1</td><td><img src="//img.atcoder.jp/assets/flag/AU.png"><a href="/users/Alice">Alice</a></td>
          <td>2008</td><td><b>1200</b></td><td>3000</td></tr></tbody></table>
          <ul class="pagination"><li><a href="/ranking/all?f.Country=AU&page=2">2</a></li></ul>'''
        self.assertEqual(parse_ac_roster(html, 1), ([('Alice', 1200)], True))
        self.assertEqual(parse_ac_roster(html, 2), ([('Alice', 1200)], False))
        with self.assertRaises(UpstreamError):
            parse_ac_roster(html.replace('/AU.png', '/NZ.png'), 1)
        with self.assertRaises(UpstreamError):
            parse_ac_roster('<html>Cloudflare challenge</html>', 1)

    @patch('holy.upstream.fetch')
    def test_cf_roster_streams_and_checks_threshold_and_country(self, get):
        response = Mock(raw=BytesIO(b'{"status":"OK","result":['
            b'{"handle":"Alice","country":"Australia","rating":1200},'
            b'{"handle":"Bob","country":"Australia","rating":1199},'
            b'{"handle":"Carol","country":"New Zealand","rating":3000}]}'))
        get.return_value.__enter__.return_value = response
        self.assertEqual(cf_roster(), [('Alice', 1200)])
        self.assertTrue(get.call_args.kwargs['stream'])
        response.raw = BytesIO(b'{"status":"FAILED","comment":"Busy"}')
        with self.assertRaises(UpstreamError):
            cf_roster()

    @patch('holy.upstream.requests.get')
    def test_no_redirect_or_inline_retry_and_retry_after(self, get):
        get.return_value = Mock(status_code=429, headers={'Retry-After': '900'})
        with self.assertRaises(UpstreamError) as context:
            fetch('https://codeforces.com/api/user.status')
        self.assertEqual(context.exception.retry_after, 900)
        get.assert_called_once()
        self.assertFalse(get.call_args.kwargs['allow_redirects'])
        get.return_value = Mock(status_code=302, headers={})
        with self.assertRaises(UpstreamError):
            fetch('https://atcoder.jp/users/alice')

    def test_atcoder_low_difficulty_conversion(self):
        self.assertEqual(display_difficulty(400), 400)
        self.assertEqual(display_difficulty(1200), 1200)
        self.assertEqual(display_difficulty(0), 147)


class DataTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.alice = Account.objects.create(platform='cf', handle='Alice', handle_key='alice', is_peer=True, rating=1500)
        self.problem = Problem.objects.create(platform='cf', key='100/A', contest='100', title='Alpha', difficulty=1600)

    def test_replayed_and_out_of_order_submissions_never_lose_ac(self):
        save_activity(self.alice, self.problem, int(self.now.timestamp()), False)
        save_activity(self.alice, self.problem, int((self.now - timedelta(days=2)).timestamp()), True)
        save_activity(self.alice, self.problem, int((self.now - timedelta(days=5)).timestamp()), False)
        self.assertEqual(Activity.objects.count(), 1)
        value = Activity.objects.get()
        self.assertEqual(int(value.last_attempt.timestamp()), int(self.now.timestamp()))
        self.assertEqual(int(value.last_ac.timestamp()), int((self.now - timedelta(days=2)).timestamp()))

    def test_removed_roster_member_is_retained_for_comparison(self):
        update_roster('cf', [('Bob', 1200)], self.now)
        self.alice.refresh_from_db()
        self.assertFalse(self.alice.is_peer)
        self.assertTrue(Account.objects.get(handle_key='bob').is_peer)
        self.assertEqual(Account.objects.count(), 2)

    def test_partial_atcoder_roster_does_not_retire_previous_pages(self):
        self.alice.platform = 'ac'
        self.alice.roster_seen = self.now - timedelta(days=1)
        self.alice.save()
        update_roster('ac', [('Bob', 2000)], self.now, final=False)
        self.alice.refresh_from_db()
        self.assertTrue(self.alice.is_peer)
        update_roster('ac', [('Carol', 1200)], self.now, final=True)
        self.alice.refresh_from_db()
        self.assertFalse(self.alice.is_peer)
        self.assertTrue(Account.objects.get(handle_key='bob').is_peer)

    @patch('holy.collector.upstream.cf_api')
    def test_recent_peer_stops_at_old_page_but_target_backfills_lifetime(self, api):
        api.return_value = [{'creationTimeSeconds': int((self.now - timedelta(days=100)).timestamp()),
                             'verdict': 'OK', 'problem': {'contestId': 100, 'index': 'A', 'name': 'Alpha'}}]
        job = enqueue('user:alice', 'submissions', account=self.alice)
        self.assertIsNone(submissions(job, self.now))
        self.alice.refresh_from_db()
        self.assertFalse(self.alice.history_complete)
        self.assertEqual(Activity.objects.count(), 0)
        self.alice.comparison_requested = self.now
        self.alice.save()
        job.account = self.alice
        self.assertIsNone(submissions(job, self.now))
        self.alice.refresh_from_db()
        self.assertTrue(self.alice.history_complete)
        self.assertIsNotNone(Activity.objects.get().last_ac)

    @patch('holy.collector.cf_problem')
    @patch('holy.collector.save_activity')
    @patch('holy.collector.upstream.cf_api')
    def test_cf_full_history_paginates_without_false_completion(self, api, save, problem):
        self.alice.comparison_requested = self.now
        self.alice.save()
        api.return_value = [{'creationTimeSeconds': int(self.now.timestamp()), 'problem': {'contestId': 100}, 'verdict': 'OK'}] * 1000
        job = enqueue('cf-pages', 'submissions', account=self.alice)
        payload = submissions(job, self.now)
        self.assertEqual(payload['offset'], 1001)
        self.assertTrue(payload['full'])
        self.alice.refresh_from_db()
        self.assertFalse(self.alice.history_complete)
        job.payload = payload
        api.return_value = []
        self.assertIsNone(submissions(job, self.now))
        self.assertEqual(api.call_args.kwargs['from'], 1001)
        self.alice.refresh_from_db()
        self.assertTrue(self.alice.history_complete)

    @patch('holy.collector.save_activity')
    @patch('holy.collector.upstream.ac_submissions')
    def test_atcoder_boundary_second_is_inclusive_and_duplicates_are_safe(self, api, save):
        self.alice.platform = 'ac'
        self.alice.verified = True
        self.alice.comparison_requested = self.now
        self.alice.save()
        api.return_value = [{'id': i, 'epoch_second': i + 1000, 'problem_id': 'abc100_a', 'contest_id': 'abc100', 'result': 'AC'} for i in range(500)]
        job = enqueue('ac-pages', 'submissions', account=self.alice)
        payload = submissions(job, self.now)
        self.assertEqual(payload['cursor'], 1499)  # Not 1500: preserve boundary submissions.
        self.assertFalse(Account.objects.get(pk=self.alice.pk).history_complete)
        job.payload = payload
        api.return_value = [api.return_value[-1]]
        self.assertIsNone(submissions(job, self.now))
        api.assert_called_with('Alice', 1499)
        self.assertTrue(Account.objects.get(pk=self.alice.pk).history_complete)

    @patch('holy.collector.save_activity')
    @patch('holy.collector.upstream.ac_submissions')
    def test_dense_atcoder_second_is_an_error_not_a_skipped_page(self, api, save):
        self.alice.platform = 'ac'
        self.alice.verified = True
        self.alice.comparison_requested = self.now
        self.alice.save()
        job = enqueue('ac-dense', 'submissions', account=self.alice, payload={'full': True, 'since': 0, 'cursor': 1000, 'latest': 0})
        api.return_value = [{'id': i, 'epoch_second': 1000, 'problem_id': 'abc100_a', 'contest_id': 'abc100', 'result': 'WA'} for i in range(500)]
        with self.assertRaises(ValueError):
            submissions(job, self.now)
        self.assertFalse(Account.objects.get(pk=self.alice.pk).history_complete)

    @patch('holy.collector.upstream.ac_verify')
    @patch('holy.collector.upstream.ac_submissions')
    def test_atcoder_verification_consumes_separate_slot(self, api, verify):
        self.alice.platform = 'ac'
        self.alice.save()
        job = enqueue('ac-verify', 'submissions', account=self.alice)
        self.assertEqual(submissions(job, self.now), {})
        verify.assert_called_once_with('Alice')
        api.assert_not_called()

    @patch('holy.collector.upstream.ac_resource')
    def test_catalog_upserts_preserve_estimates_and_refresh_titles(self, resource):
        problem = Problem.objects.create(platform='ac', key='abc100_a', contest='abc100', title='Old', difficulty=900)
        resource.return_value = [{'id': 'abc100_a', 'contest_id': 'abc100', 'title': 'New'}]
        execute(enqueue('catalog', 'ac_problems'), self.now)
        execute(Job.objects.get(key='catalog'), self.now)
        problem.refresh_from_db()
        self.assertEqual((problem.title, problem.difficulty), ('New', 900))
        resource.return_value = {'abc100_a': {'difficulty': 0}}
        execute(enqueue('models', 'ac_models'), self.now)
        problem.refresh_from_db()
        self.assertEqual(problem.difficulty, 147)

    def test_query_promotion_preserves_pagination_and_backoff(self):
        job = enqueue('user', 'submissions', account=self.alice, payload={'offset': 1001}, now=self.now + timedelta(hours=1))
        enqueue('user', 'submissions', account=self.alice, priority=1)
        job.refresh_from_db()
        self.assertEqual(job.priority, 1)
        self.assertEqual(job.payload, {'offset': 1001})
        self.assertEqual(job.ready_at, self.now + timedelta(hours=1))


class WorkerTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.settings = override_settings(BASE_DIR=self.directory.name)
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        self.state = CollectorState.objects.create(next_request_at=self.now, lease_until=self.now, maintenance_at=self.now)
        self.job = enqueue('cf_roster', 'cf_roster', now=self.now)

    @patch('holy.collector.execute', return_value=None)
    def test_gate_persists_across_calls_and_covers_all_platforms(self, execute):
        self.assertIn('updated', run_one(self.now))
        enqueue('ac_roster', 'ac_roster', now=self.now)
        self.assertIn('Waiting', run_one(self.now + timedelta(seconds=179)))
        execute.assert_called_once()
        self.state.refresh_from_db()
        self.assertGreaterEqual(self.state.next_request_at, self.now + timedelta(seconds=180))

    @patch('holy.collector.execute', side_effect=UpstreamError('Rate limited', retry_after=900))
    def test_failure_keeps_cache_and_respects_global_retry_after(self, execute):
        self.assertIn('retry later', run_one(self.now))
        self.job.refresh_from_db()
        self.state.refresh_from_db()
        self.assertEqual(self.job.failures, 1)
        self.assertGreaterEqual(self.job.ready_at, self.now + timedelta(seconds=900))
        enqueue('ac_roster', 'ac_roster', now=self.now)
        self.assertIn('Waiting', run_one(self.now + timedelta(seconds=899)))
        execute.assert_called_once()

    @patch('holy.collector.execute')
    def test_live_lease_blocks_restart_until_expiry(self, execute):
        self.state.lease_until = self.now + timedelta(minutes=15)
        self.state.save()
        self.assertIn('Waiting', run_one(self.now))
        execute.assert_not_called()

    def test_idle_worker_still_updates_heartbeat(self):
        Job.objects.update(ready_at=self.now + timedelta(days=1))
        self.assertEqual(run_one(self.now), 'Queue idle')
        self.state.refresh_from_db()
        self.assertEqual(self.state.last_heartbeat, self.now)
        self.assertIsNone(self.state.last_finished)

    def test_schedule_is_deduplicated(self):
        self.state.maintenance_at = None
        self.state.save()
        schedule(self.now)
        schedule(self.now + timedelta(minutes=2))
        self.assertEqual(Job.objects.count(), 5)


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class PageTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.alice = Account.objects.create(platform='cf', handle='Alice', handle_key='alice', is_peer=True, rating=1200, synced_at=self.now)
        self.bob = Account.objects.create(platform='cf', handle='Bob', handle_key='bob', is_peer=True, rating=1800, synced_at=self.now)
        self.me = Account.objects.create(platform='cf', handle='Me', handle_key='me', history_complete=True, synced_at=self.now)
        self.high = Problem.objects.create(platform='cf', key='1/A', contest='1', title='High', difficulty=2400)
        self.low = Problem.objects.create(platform='cf', key='2/A', contest='2', title='Low', difficulty=1200)
        self.unknown = Problem.objects.create(platform='cf', key='3/A', contest='3', title='Unknown')
        for problem in (self.high, self.low, self.unknown):
            Activity.objects.create(account=self.alice, problem=problem, last_attempt=self.now, last_ac=self.now)
        Activity.objects.create(account=self.bob, problem=self.high, last_attempt=self.now)

    @patch('holy.upstream.requests.get', side_effect=AssertionError('Web requests must not fetch upstreams'))
    def test_sorted_counts_unique_users_and_expandable_handles(self, get):
        response = self.client.get('/holy-competitive/')
        rows = list(response.context['page'])
        self.assertEqual([r['problem'].title for r in rows], ['High', 'Low', 'Unknown'])
        self.assertEqual((rows[0]['count'], rows[0]['solved_count'], rows[0]['trying_count']), (2, 1, 1))
        self.assertContains(response, 'Bob')
        self.assertContains(response, 'https://codeforces.com/problemset/problem/1/A')
        get.assert_not_called()

    def test_excludes_all_time_ac_not_only_recent_month(self):
        old = self.now - timedelta(days=365)
        Activity.objects.create(account=self.me, problem=self.high, last_attempt=old, last_ac=old)
        response = self.client.get('/holy-competitive/?cf=mE')
        self.assertEqual([r['problem'].title for r in response.context['page']], ['Low', 'Unknown'])

    def test_old_peer_activity_and_ineligible_accounts_are_excluded(self):
        Activity.objects.filter(problem=self.low).update(last_attempt=self.now - timedelta(days=31))
        self.bob.is_peer = False
        self.bob.save()
        response = self.client.get('/holy-competitive/')
        self.assertEqual(response.context['page'].paginator.count, 2)
        self.assertEqual(list(response.context['page'])[0]['count'], 1)

    def test_incomplete_history_does_not_claim_problems_are_unsolved(self):
        self.me.history_complete = False
        self.me.save()
        response = self.client.get('/holy-competitive/?cf=Me')
        self.assertTrue(response.context['pending'])
        self.assertEqual(response.context['page'].paginator.count, 0)
        self.assertContains(response, '暂不把任何题标成')

    def test_earlier_ac_with_recent_resubmission_is_not_a_recent_ac_or_trying(self):
        Activity.objects.filter(account=self.alice, problem=self.low).update(last_ac=self.now - timedelta(days=100))
        response = self.client.get('/holy-competitive/?mode=solved')
        self.assertNotIn(self.low.pk, [r['problem'].pk for r in response.context['page']])
        response = self.client.get('/holy-competitive/?mode=trying')
        self.assertEqual([r['problem'].pk for r in response.context['page']], [self.high.pk])

    def test_search_min_difficulty_user_count_and_trying_mode(self):
        response = self.client.get('/holy-competitive/?mode=trying&min=2000&users=2&q=High')
        self.assertEqual(response.context['page'].paginator.count, 1)
        self.assertEqual(self.client.get('/holy-competitive/?min=2500').context['page'].paginator.count, 0)
        self.assertEqual(self.client.get('/holy-competitive/?mode=solved').context['page'].paginator.count, 3)

    @patch('holy.upstream.requests.get', side_effect=AssertionError('No upstream HTTP from query'))
    def test_dual_handle_post_is_deduplicated_case_insensitive_and_queued(self, get):
        self.client.post('/holy-competitive/query/', {'cf': 'Someone', 'ac': 'AtUser'})
        self.client.post('/holy-competitive/query/', {'cf': 'someone', 'ac': 'atuser'})
        self.assertEqual(Account.objects.filter(handle_key__in=['someone', 'atuser']).count(), 2)
        self.assertEqual(Job.objects.count(), 2)
        self.assertTrue(all(job.priority == 1 for job in Job.objects.all()))
        get.assert_not_called()

    def test_cached_get_and_polling_are_read_only(self):
        self.client.get('/holy-competitive/?cf=unknown')
        response = self.client.get('/holy-competitive/status/?cf=unknown')
        self.assertIsNone(response.json()['accounts']['cf'])
        self.assertEqual(Job.objects.count(), 0)
        self.assertEqual(Account.objects.count(), 3)

    def test_query_validation_csrf_and_persistent_budget(self):
        secure = Client(enforce_csrf_checks=True)
        self.assertEqual(secure.post('/holy-competitive/query/', {'cf': 'Alice'}).status_code, 403)
        self.assertEqual(self.client.get('/holy-competitive/query/').status_code, 405)
        response = self.client.post('/holy-competitive/query/', {'cf': '../../evil'})
        self.assertIn('error=', response.url)
        self.assertEqual(Job.objects.count(), 0)
        for i in range(21):
            response = self.client.post('/holy-competitive/query/', {'cf': f'u{i}'})
        self.assertIn('error=', response.url)
        self.assertEqual(QueryBudget.objects.get().count, 20)
        self.assertEqual(Job.objects.count(), 20)

    def test_platform_isolation_and_atcoder_link(self):
        at = Account.objects.create(platform='ac', handle='Alice', handle_key='alice', is_peer=True, rating=1200)
        problem = Problem.objects.create(platform='ac', key='abc100_a', contest='abc100', title='AtCoder', difficulty=1400)
        Activity.objects.create(account=at, problem=problem, last_attempt=self.now)
        response = self.client.get('/holy-competitive/?platform=ac&cf=Me')
        self.assertEqual(response.context['page'].paginator.count, 1)
        self.assertContains(response, 'https://atcoder.jp/contests/abc100/tasks/abc100_a')

    def test_atcoder_only_query_selects_atcoder_tab(self):
        response = self.client.post('/holy-competitive/query/', {'ac': 'AtOnly'})
        self.assertIn('platform=ac', response.url)

    def test_gym_problem_url(self):
        gym = Problem(platform='cf', key='100001/A', contest='100001', title='Gym')
        self.assertEqual(gym.url, 'https://codeforces.com/gym/100001/problem/A')

    def test_home_and_navigation_link_to_new_section(self):
        self.assertContains(self.client.get('/'), '/holy-competitive/')
