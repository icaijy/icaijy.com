import json
from collections import Counter

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import VCEAttempt
from .question_bank import LETTERS, QUESTION_BY_ID, QUESTIONS, TOPIC_LABELS
from .views import SESSION_KEY


class QuestionBankTests(TestCase):
    def test_bank_is_large_balanced_and_well_formed(self):
        self.assertGreaterEqual(len(QUESTIONS), 350)
        self.assertEqual(len({q["id"] for q in QUESTIONS}), len(QUESTIONS))
        self.assertEqual(len({q["stem"] for q in QUESTIONS}), len(QUESTIONS))
        counts = Counter(q["topic"] for q in QUESTIONS)
        self.assertEqual(set(counts), set(TOPIC_LABELS))
        self.assertGreaterEqual(min(counts.values()), 10)
        for question in QUESTIONS:
            self.assertEqual(len(question["options"]), 4)
            self.assertEqual(len(question["explanations"]), 4)
            self.assertIn(question["answer"], LETTERS)
            self.assertTrue(question["source"])
            self.assertNotIn("2025", question["source"])

    def test_question_lookup_matches_ids(self):
        for question in QUESTIONS:
            self.assertIs(QUESTION_BY_ID[question["id"]], question)


class SpeedrunProtocolTests(TestCase):
    def setUp(self):
        self.start_url = reverse("vce:start")
        self.answer_url = reverse("vce:answer")
        self.finish_url = reverse("vce:finish")

    def start(self):
        response = self.client.post(
            self.start_url,
            data=json.dumps({"display_name": "Test Swan"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        return response

    def test_start_does_not_leak_answer(self):
        payload = self.start().json()
        self.assertIn("question", payload)
        self.assertNotIn("answer", payload["question"])
        self.assertNotIn("explanations", payload["question"])

    def test_server_scores_correct_answer(self):
        payload = self.start().json()
        qid = payload["question"]["id"]
        correct = QUESTION_BY_ID[qid]["answer"]
        response = self.client.post(
            self.answer_url,
            data=json.dumps({"question_id": qid, "choice": correct}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result["correct"])
        self.assertEqual(result["score"], 1)

    def test_wrong_answer_enforces_three_second_lock(self):
        payload = self.start().json()
        qid = payload["question"]["id"]
        correct = QUESTION_BY_ID[qid]["answer"]
        wrong = next(letter for letter in LETTERS if letter != correct)
        response = self.client.post(
            self.answer_url,
            data=json.dumps({"question_id": qid, "choice": wrong}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertFalse(result["correct"])
        next_qid = result["next_question"]["id"]
        next_correct = QUESTION_BY_ID[next_qid]["answer"]
        blocked = self.client.post(
            self.answer_url,
            data=json.dumps({"question_id": next_qid, "choice": next_correct}),
            content_type="application/json",
        )
        self.assertEqual(blocked.status_code, 429)

    def test_finish_persists_server_state(self):
        payload = self.start().json()
        qid = payload["question"]["id"]
        correct = QUESTION_BY_ID[qid]["answer"]
        self.client.post(
            self.answer_url,
            data=json.dumps({"question_id": qid, "choice": correct}),
            content_type="application/json",
        )
        session = self.client.session
        state = session[SESSION_KEY]
        state["deadline_ts"] = 0
        session[SESSION_KEY] = state
        session.save()

        response = self.client.post(self.finish_url, data="{}", content_type="application/json")
        self.assertEqual(response.status_code, 201)
        attempt = VCEAttempt.objects.get()
        self.assertEqual(attempt.score, 1)
        self.assertEqual(attempt.display_name, "Test Swan")
        self.assertGreaterEqual(len(attempt.question_ids), 2)

    def test_authenticated_attempt_uses_account_identity(self):
        user = get_user_model().objects.create_user(username="speedy", password="x")
        self.client.force_login(user)
        self.start()
        session = self.client.session
        state = session[SESSION_KEY]
        state["deadline_ts"] = 0
        session[SESSION_KEY] = state
        session.save()
        self.client.post(self.finish_url, data="{}", content_type="application/json")
        attempt = VCEAttempt.objects.get()
        self.assertEqual(attempt.user, user)
        self.assertEqual(attempt.display_name, "")
