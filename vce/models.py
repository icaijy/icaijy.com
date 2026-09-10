from django.conf import settings
from django.db import models


class VCEAttempt(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="vce_speedruns",
        null=True,
        blank=True,
    )
    display_name = models.CharField(max_length=32, blank=True)
    score = models.PositiveIntegerField(default=0)
    wrong_count = models.PositiveIntegerField(default=0)
    elapsed_ms = models.PositiveIntegerField(default=60000)
    question_ids = models.JSONField(default=list)
    answers = models.JSONField(default=list)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-score", "wrong_count", "completed_at", "id")
        indexes = [
            models.Index(
                fields=("-score", "wrong_count", "completed_at"),
                name="vce_hof_rank_idx",
            ),
            models.Index(
                fields=("user", "-completed_at"),
                name="vce_user_run_idx",
            ),
        ]

    @property
    def public_name(self):
        if self.user_id:
            return self.user.username
        return f"{self.display_name or 'Guest Swan'} · guest"

    def __str__(self):
        return f"{self.public_name}: {self.score} correct"
