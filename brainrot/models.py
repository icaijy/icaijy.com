import uuid

from django.conf import settings
from django.db import models

from .storage import private_media_storage


def hall_of_fame_upload_path(instance, filename):
    extension = getattr(instance, '_validated_extension', 'webm')
    return f'hall_of_fame/{uuid.uuid4().hex}.{extension}'


class HallOfFameEntry(models.Model):
    class State(models.TextChoices):
        PENDING = 'pending', 'Pending review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hall_of_fame_entries',
        null=True,
        blank=True,
    )
    display_name = models.CharField(max_length=32, blank=True)
    score = models.PositiveSmallIntegerField()
    video = models.FileField(
        upload_to=hall_of_fame_upload_path,
        storage=private_media_storage,
    )
    mime_type = models.CharField(max_length=32)
    duration_seconds = models.FloatField()
    event_timeline = models.JSONField(default=list, blank=True)
    state = models.CharField(max_length=12, choices=State.choices, default=State.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('-score', 'created_at')
        indexes = [
            models.Index(fields=('state', '-score', 'created_at'), name='hof_public_rank_idx'),
            models.Index(fields=('user', '-created_at'), name='hof_user_rate_idx'),
        ]

    def __str__(self):
        return f'{self.public_name}: {self.score} ({self.state})'

    @property
    def public_name(self):
        if self.user_id:
            return self.user.username
        return f'{self.display_name or "Anonymous Swan"} · guest'


class HallOfFameUploadAttempt(models.Model):
    """Small audit/rate-limit row; failed uploads must count as attempts too."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    client_key = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=('user', '-created_at'), name='hof_attempt_rate_idx'),
            models.Index(fields=('client_key', '-created_at'), name='hof_attempt_client_idx'),
        ]
