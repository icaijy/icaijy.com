from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import AlgorithmicsRun
from .question_bank import QUESTION_BY_ID, QUESTIONS


class QuestionBankTests(TestCase):
    def test_bank_is_large_valid_and_original(self):
        self.assertGreaterEqual(len(QUESTIONS), 250)
        self.assertEqual(len(QUESTIONS), len(QUESTION_BY_ID))
        for question in QUESTIONS:
            self.assertEqual(len(question.options), 4)
            self.assertEqual(len(question.explanations), 4)
            self.assertIn(question.answer, question.options)
            self.assertTrue(question.source.startswith('Written for icaijy.com'))


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class SpeedrunTests(TestCase):
    def test_entry_points_and_public_payload_hide_answers(self):
        page = self.client.get(reverse('vce:index'))
        self.assertContains(page, 'VCE Algorithmics 1 Minute Speedrun')
        self.assertContains(self.client.get('/'), '/vce/')
        started = self.client.post(reverse('vce:start')).json()
        self.assertNotIn('answer', started['question'])
        self.assertNotIn('explanations', started['question'])

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
        self.assertContains(detail, question.prompt)

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
