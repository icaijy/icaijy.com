from django.db import models
from math import nan


class Problem(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    time_limit = models.FloatField(default=1.0)       # 秒
    memory_limit = models.IntegerField(default=256)   # MB
    test_cases_file = models.FileField(upload_to='testcases/', null=True, blank=True)

    def __str__(self):
        return self.title

STATUS_CHOICES = [
    ('PENDING','Pending'),
    ('AC','AC'),
    ('WA','WA'),
    ('TLE','TLE'),
    ('RE','RE'),
    ('CE','CE'),
]

from django.contrib.auth.models import User

class Submission(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    username = models.CharField(max_length=100, default='Anonymous')
    language = models.CharField(max_length=10)
    code = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    result = models.JSONField(null=True, blank=True)
    submit_time = models.DateTimeField(auto_now_add=True)
    elapsed_time = models.FloatField(default=-1)  # 秒，-1 表示练习模式
    kpm = models.FloatField(null=True)  # 每分钟键击次数，-1 表示未记录


