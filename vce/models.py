import uuid

from django.conf import settings
from django.db import models

from brainrot.storage import private_media_storage


def vce_run_upload_path(instance, filename):
    extension = getattr(instance, '_validated_extension', 'webm')
    return f'vce_runs/{uuid.uuid4().hex}.{extension}'


class AlgorithmicsRun(models.Model):
    class GameMode(models.TextChoices):
        NORMAL = 'normal', 'Serious'
        SIX_SEVEN = 'six_seven', '67'
        LEG_CLAPS = 'leg_claps', 'Tung Tung'
        COMBINE = 'combine', 'Combine'

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
    bank_id = models.CharField(max_length=48, default='algorithmics_u34')
    game_mode = models.CharField(max_length=16, choices=GameMode.choices, default=GameMode.NORMAL)
    movement_score = models.PositiveIntegerField(default=1)
    final_score = models.PositiveIntegerField(default=0)
    metrics = models.JSONField(default=dict)
    question_ids = models.JSONField(default=list)
    attempts = models.JSONField(default=list)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)
    is_submitted = models.BooleanField(default=False)
    video = models.FileField(upload_to=vce_run_upload_path, storage=private_media_storage, blank=True)
    video_mime_type = models.CharField(max_length=32, blank=True)
    video_duration_seconds = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ('-final_score', 'finished_at', 'id')
        indexes = [
            models.Index(fields=('bank_id', 'game_mode', '-final_score'), name='vce_bank_score_idx'),
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

    @property
    def is_physical(self):
        return self.game_mode != self.GameMode.NORMAL
