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
        self.assertGreaterEqual(len(ALL_QUESTIONS), 1000)
        self.assertTrue({question.id for question in ALL_QUESTIONS} <= QUESTION_BY_ID.keys())
        self.assertEqual(len(BANKS), 13)
        for bank in BANKS.values():
            signatures = {(question.prompt, question.options) for question in bank.questions}
            self.assertEqual(len(signatures), len(bank.questions))
            for question in bank.questions:
                self.assertEqual(len(question.options), 4)
                self.assertEqual(len(set(question.options)), 4)
                self.assertEqual(len(question.explanations), 4)
                self.assertIn(question.answer, question.options)
                self.assertTrue(question.source.startswith('Written for icaijy.com'))

    def test_cosmetic_clones_are_not_offered_but_old_run_ids_still_resolve(self):
        for bank_id, bank in BANKS.items():
            if bank_id == 'algorithmics_u34':
                continue
            self.assertFalse(any(question.id.endswith(('-1', '-2', '-3')) for question in bank.questions))
            self.assertFalse(any(question.prompt.startswith((
                'A student is checking a worked solution.',
                'Which response best completes this VCE-style item?',
                'During a one-minute revision round:',
            )) for question in bank.questions))
        self.assertIn('chemistry_u12-00-1', QUESTION_BY_ID)
        self.assertIn('galvanic cell', QUESTION_BY_ID['chemistry_u34-32-0'].prompt)
        self.assertIn('lurches forward', QUESTION_BY_ID['physics_u34-24-0'].prompt)
        self.assertIn('maximum', QUESTION_BY_ID['methods_u34_techactive-16-0'].prompt)

    def test_methods_banks_exclude_general_mathematics_topics(self):
        forbidden = {'Finance', 'Regression', 'Residuals', 'Sequences'}
        for bank_id, bank in BANKS.items():
            if bank_id.startswith('methods_'):
                self.assertFalse(forbidden & {question.topic.rsplit(' · ', 1)[-1] for question in bank.questions})

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
    def test_prepare_delivers_twenty_complete_questions_and_refill_has_no_duplicates(self):
        prepared = self.client.post(reverse('vce:prepare'), {'bank_id': 'algorithmics_u34'}).json()
        self.assertEqual(len(prepared['questions']), 20)
        self.assertIn('answer_index', prepared['questions'][0])
        self.assertIn('explanations', prepared['questions'][0])
        first_ids = {question['id'] for question in prepared['questions']}

        refill = self.client.post(reverse('vce:refill'), {'token': prepared['token']}).json()
        self.assertEqual(len(refill['questions']), 20)
        refill_ids = {question['id'] for question in refill['questions']}
        self.assertFalse(first_ids & refill_ids)
        run = AlgorithmicsRun.objects.get(token=prepared['token'])
        self.assertEqual(len(run.question_ids), 40)

    def test_prepare_spreads_questions_across_topics(self):
        prepared = self.client.post(reverse('vce:prepare'), {'bank_id': 'algorithmics_u34'}).json()
        self.assertEqual(len({question['topic'] for question in prepared['questions']}), 20)

    def test_prepared_run_starts_clock_only_when_start_is_clicked(self):
        prepared = self.client.post(reverse('vce:prepare'), {'bank_id': 'physics_u34'}).json()
        run = AlgorithmicsRun.objects.get(token=prepared['token'])
        old_started_at = run.started_at
        started = self.client.post(reverse('vce:start'), {
            'token': prepared['token'], 'bank_id': 'physics_u34', 'game_mode': 'normal',
        })
        self.assertEqual(started.status_code, 200)
        run.refresh_from_db()
        self.assertGreater(run.started_at, old_started_at)
        self.assertNotIn('question', started.json())

    def test_frontend_attempt_batch_saves_final_unanswered_question(self):
        prepared = self.client.post(reverse('vce:prepare')).json()
        self.client.post(reverse('vce:start'), {'token': prepared['token']})
        run = AlgorithmicsRun.objects.get(token=prepared['token'])
        run.started_at = timezone.now() - timedelta(seconds=61)
        run.save(update_fields=('started_at',))
        question_ids = run.question_ids[:3]
        attempts = [
            {'question_id': question_ids[0], 'selected': 0, 'correct': True, 'answered_ms': 1200},
            {'question_id': question_ids[1], 'selected': 3, 'correct': False, 'answered_ms': 4200},
            {'question_id': question_ids[2], 'selected': None, 'correct': None, 'answered_ms': 60000},
        ]
        response = self.client.post(reverse('vce:finish'), {
            'token': prepared['token'], 'attempts': __import__('json').dumps(attempts),
        })
        self.assertEqual(response.status_code, 200)
        run.refresh_from_db()
        self.assertEqual(run.score, 1)
        self.assertIsNone(run.attempts[-1]['selected'])
        detail = self.client.get(response.json()['detail_url'])
        self.assertContains(detail, 'not answered before time expired')

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
