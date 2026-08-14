from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Problem, Submission


@override_settings(OJ_ENABLED=False)
class RetiredOJTests(TestCase):
    def test_root_and_legacy_routes_are_retired(self):
        self.assertEqual(self.client.get('/oj/').status_code, 410)
        self.assertEqual(self.client.get('/oj/problem/999/').status_code, 410)

    def test_post_cannot_create_submission(self):
        Problem.objects.create(title='nope', description='retired')
        response = self.client.post('/oj/problem/1/', {'language': 'cpp', 'code': 'int main(){}'})
        self.assertEqual(response.status_code, 410)
        self.assertEqual(Submission.objects.count(), 0)

# Create your tests here.
