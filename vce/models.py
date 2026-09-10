import uuid

from django.conf import settings
from django.db import models


class AlgorithmicsRun(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='algorithmics_speedruns',
    )
    display_name = models.CharField(max_length=32, blank=True)
    session_key = models.CharField(max_length=40, blank=True)
    score = models.PositiveSmallIntegerField(default=0)
    question_ids = models.JSONField(default=list)
    attempts = models.JSONField(default=list)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)
    is_submitted = models.BooleanField(default=False)

    class Meta:
        ordering = ('-score', 'finished_at', 'id')
        indexes = [
            models.Index(fields=('-score', 'finished_at'), name='vce_run_score_idx'),
            models.Index(fields=('token',), name='vce_run_token_idx'),
        ]

    @property
    def public_name(self):
        if self.user_id:
            return self.user.username
        return f'{self.display_name or "Anonymous Student"} · guest'

    @property
    def elapsed_seconds(self):
        end = self.finished_at or self.started_at
        return max(0, (end - self.started_at).total_seconds())
