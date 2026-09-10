from datetime import timedelta

from django.test import TestCase, override_settings
from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils import timezone

from .models import AlgorithmicsRun
from .question_bank import ALL_QUESTIONS, BANKS, QUESTION_BY_ID, QUESTIONS, latexify


class QuestionBankTests(TestCase):
    def test_bank_is_large_valid_and_original(self):
        self.assertGreaterEqual(len(QUESTIONS), 250)
        self.assertGreaterEqual(len(ALL_QUESTIONS), 1500)
        self.assertEqual(len(ALL_QUESTIONS), len(QUESTION_BY_ID))
        self.assertEqual(len(BANKS), 13)
        for question in ALL_QUESTIONS:
            self.assertEqual(len(question.options), 4)
            self.assertEqual(len(set(question.options)), 4)
            self.assertEqual(len(question.explanations), 4)
            self.assertIn(question.answer, question.options)
            self.assertTrue(question.source.startswith('Written for icaijy.com'))

    def test_only_mathematics_banks_are_split_by_technology(self):
        split_banks = [bank for bank in BANKS.values() if bank.technology]
        self.assertEqual(len(split_banks), 8)
        self.assertTrue(all(bank.subject in {'Mathematical Methods', 'Specialist Mathematics'} for bank in split_banks))
        self.assertFalse(BANKS['chemistry_u12'].technology)
        self.assertFalse(BANKS['physics_u34'].technology)

    def test_formulae_are_rendered_as_mathjax_tex(self):
        self.assertEqual(latexify('O(n² log n)'), r'\(O(n^2 \log n)\)')
        self.assertIn(r'\(T(n)=2T(n/2)+O(n^1)\)', latexify('Find T(n) = 2T(n/2) + O(n^1) now'))


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class SpeedrunTests(TestCase):
    def test_entry_points_and_public_payload_hide_answers(self):
        page = self.client.get(reverse('vce:index'))
        self.assertContains(page, 'Pick a question bank')
        self.assertContains(page, 'Mathematical Methods')
        self.assertContains(page, 'Tech-free')
        self.assertContains(self.client.get(reverse('vce_chaos:index')), '67 × VCE')
        self.assertContains(self.client.get('/'), '/vce/')
        started = self.client.post(reverse('vce:start'), {'bank_id': 'chemistry_u12'}).json()
        self.assertEqual(started['bank_id'], 'chemistry_u12')
        self.assertNotIn('answer', started['question'])
        self.assertNotIn('explanations', started['question'])

    def test_67vce_is_canonical_and_legacy_routes_redirect(self):
        self.assertEqual(reverse('vce_chaos:index'), '/67vce/')
        self.assertEqual(self.client.get('/67xvce/').headers['Location'], '/67vce/')
        legacy_bank = self.client.get('/67xvce/physics_u34/')
        self.assertEqual(legacy_bank.status_code, 301)
        self.assertEqual(legacy_bank.headers['Location'], '/67vce/physics_u34/')

    def test_play_page_loads_repeatable_mathjax_and_camera_preview_hooks(self):
        page = self.client.get(reverse('vce_chaos:play', args=('algorithmics_u34',)))
        self.assertContains(page, 'mathjax@3/es5/tex-chtml.js')
        self.assertContains(page, 'data-camera-panel')
        self.assertContains(page, 'data-sidebar="tools"')

    def test_legacy_physical_run_without_video_is_preserved_and_labelled(self):
        run = AlgorithmicsRun.objects.create(
            session_key='legacy', game_mode='six_seven', bank_id='algorithmics_u34',
            score=2, movement_score=3, final_score=6, is_submitted=True,
        )
        detail = self.client.get(reverse('vce:run_detail', args=(run.token,)))
        self.assertContains(detail, 'Legacy run · no video was recorded')
        self.assertEqual(self.client.get(reverse('vce:run_video', args=(run.token,))).status_code, 404)

    def test_saved_vce_video_can_be_streamed(self):
        run = AlgorithmicsRun.objects.create(
            session_key='video', game_mode='six_seven', bank_id='algorithmics_u34',
            final_score=1, is_submitted=True, video_mime_type='video/webm',
        )
        run.video.save('evidence.webm', ContentFile(b'video-evidence'), save=True)
        response = self.client.get(reverse('vce:run_video', args=(run.token,)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'video/webm')

    def test_play_pages_include_the_official_reference(self):
        algorithmics = self.client.get(reverse('vce:play', args=('algorithmics_u34',)))
        self.assertContains(algorithmics, 'MASTER THEOREM')
        self.assertContains(algorithmics, r'aT\!\left')
        chemistry = self.client.get(reverse('vce:play', args=('chemistry_u34',)))
        self.assertContains(chemistry, '2026 VCAA Chemistry Data Book')
        self.assertContains(chemistry, '2026-ChemistryDataBook_0.pdf')
        self.assertEqual(self.client.get(reverse('vce:play', args=('not-a-bank',))).status_code, 404)

    def test_start_answer_finish_and_review(self):
        started = self.client.post(reverse('vce:start')).json()
        question = QUESTION_BY_ID[started['question']['id']]
        response = self.client.post(reverse('vce:answer'), {
            'token': started['token'], 'position': 0, 'selected': question.answer_index,
        })
        self.assertTrue(response.json()['correct'])
        self.assertEqual(response.json()['score'], 1)

        run = AlgorithmicsRun.objects.get(token=started['token'])
        run.started_at = timezone.now() - timedelta(seconds=61)
        run.save(update_fields=('started_at',))
        finished = self.client.post(reverse('vce:finish'), {
            'token': started['token'], 'display_name': 'Fast Swan',
        })
        self.assertEqual(finished.status_code, 200)
        detail = self.client.get(finished.json()['detail_url'])
        self.assertContains(detail, 'Fast Swan')
        self.assertContains(detail, question.topic)

    def test_physical_mode_multiplies_correct_answers_by_server_counted_events(self):
        started = self.client.post(reverse('vce:start'), {'game_mode': 'combine', 'bank_id': 'physics_u34'}).json()
        question = QUESTION_BY_ID[started['question']['id']]
        self.client.post(reverse('vce:answer'), {'token': started['token'], 'position': 0, 'selected': question.answer_index})
        run = AlgorithmicsRun.objects.get(token=started['token'])
        run.started_at = timezone.now() - timedelta(seconds=61)
        run.save(update_fields=('started_at',))
        finished = self.client.post(reverse('vce:finish'), {
            'token': started['token'], 'display_name': 'Chaos Swan',
            'metrics': '{"six_seven":[1,2,3],"leg_claps":[1.5,2.5]}',
        }).json()
        self.assertEqual(finished['movement_score'], 6)
        self.assertEqual(finished['final_score'], 6)
        self.assertEqual(run.bank_id, 'physics_u34')

    def test_invalid_mode_and_movement_payload_are_rejected(self):
        self.assertEqual(self.client.post(reverse('vce:start'), {'game_mode': 'nope'}).status_code, 400)
        started = self.client.post(reverse('vce:start'), {'game_mode': 'six_seven'}).json()
        run = AlgorithmicsRun.objects.get(token=started['token'])
        run.started_at = timezone.now() - timedelta(seconds=61)
        run.save(update_fields=('started_at',))
        response = self.client.post(reverse('vce:finish'), {'token': started['token'], 'metrics': '{"six_seven":[2,1]}'})
        self.assertEqual(response.status_code, 400)

    def test_wrong_answer_enforces_three_second_lock(self):
        started = self.client.post(reverse('vce:start')).json()
        question = QUESTION_BY_ID[started['question']['id']]
        wrong = (question.answer_index + 1) % 4
        first = self.client.post(reverse('vce:answer'), {
            'token': started['token'], 'position': 0, 'selected': wrong,
        })
        self.assertFalse(first.json()['correct'])
        blocked = self.client.post(reverse('vce:answer'), {
            'token': started['token'], 'position': 1, 'selected': 0,
        })
        self.assertEqual(blocked.status_code, 429)

    def test_run_cannot_be_answered_from_another_session(self):
        started = self.client.post(reverse('vce:start')).json()
        other = self.client_class()
        response = other.post(reverse('vce:answer'), {
            'token': started['token'], 'position': 0, 'selected': 0,
        })
        self.assertEqual(response.status_code, 403)
