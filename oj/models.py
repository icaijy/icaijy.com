from django.db import models

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

class Submission(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    language = models.CharField(max_length=10)
    code = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    result = models.JSONField(null=True, blank=True)
    submit_time = models.DateTimeField(auto_now_add=True)
    elapsed_time = models.FloatField(default=-1)  # 秒，-1表示练习模式
