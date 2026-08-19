import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .storage import private_media_storage


def hall_of_fame_upload_path(instance, filename):
    extension = getattr(instance, '_validated_extension', 'mp4')
    return f'hall_of_fame/{uuid.uuid4().hex}.{extension}'


class HallOfFameEntry(models.Model):
    class GameMode(models.TextChoices):
        SIX_SEVEN = 'six_seven', _('67 Counter')
        LEG_CLAPS = 'leg_claps', _('Tung Tung Leg Claps')
        VOICE_67 = 'voice_67', _('Six Seven Voice Speedrun')

    class Visibility(models.TextChoices):
        PUBLIC = 'public', _('Public')
        PRIVATE = 'private', _('Private')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hall_of_fame_entries',
        null=True,
        blank=True,
    )
    display_name = models.CharField(max_length=32, blank=True)
    game_mode = models.CharField(
        max_length=16,
        choices=GameMode.choices,
        default=GameMode.SIX_SEVEN,
    )
    score = models.PositiveSmallIntegerField()
    video = models.FileField(
        upload_to=hall_of_fame_upload_path,
        storage=private_media_storage,
    )
    mime_type = models.CharField(max_length=32)
    duration_seconds = models.FloatField()
    event_timeline = models.JSONField(default=list, blank=True)
    visibility = models.CharField(
        max_length=12,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-score', 'created_at')
        indexes = [
            models.Index(fields=('game_mode', 'visibility', '-score', 'created_at'), name='hof_mode_public_rank_idx'),
            models.Index(fields=('user', '-created_at'), name='hof_user_rate_idx'),
        ]

    def __str__(self):
        return f'{self.public_name}: {self.score} {self.game_mode} ({self.visibility})'

    @property
    def public_name(self):
        if self.user_id:
            return self.user.username
        return f'{self.display_name or "Anonymous Swan"} · guest'


class HallOfFameComment(models.Model):
    entry = models.ForeignKey(
        HallOfFameEntry,
        on_delete=models.CASCADE,
        related_name='comments',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='hall_of_fame_comments',
        null=True,
        blank=True,
    )
    # Snapshot the visible name so a comment still has an author label if a
    # registered account is later removed. Guest comments also use this field.
    author_name = models.CharField(max_length=32)
    body = models.TextField()
    # HMAC-derived pseudonymous key for anonymous rate limiting; never a raw IP.
    client_key = models.CharField(max_length=64, blank=True)
    is_submission_note = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('created_at', 'id')
        indexes = [
            models.Index(fields=('entry', 'created_at'), name='hof_comment_entry_idx'),
            models.Index(fields=('user', 'created_at'), name='hof_comment_user_idx'),
            models.Index(fields=('client_key', 'created_at'), name='hof_comment_client_idx'),
        ]

    def __str__(self):
        return f'{self.public_name} on HOF #{self.entry_id}: {self.body[:40]}'

    @property
    def public_name(self):
        if self.user_id:
            return self.user.username
        if self.client_key:
            return f'{self.author_name or "Anonymous Swan"} · guest'
        return self.author_name or 'Deleted user'

    @property
    def rendered_body(self):
        from .comment_markup import render_comment_markdown
        return render_comment_markdown(self.body)

    @property
    def is_original_poster(self):
        if self.is_submission_note:
            return True
        return bool(self.user_id and self.entry.user_id == self.user_id)


class HallOfFameReaction(models.Model):
    class Emoji(models.TextChoices):
        YUM = '😋', '😋'
        FIRE = '🔥', '🔥'
        LAUGH = '😂', '😂'
        SKULL = '💀', '💀'

    # Every reaction keeps the owning entry for cascade cleanup. comment=None
    # means the reaction is on the run itself; otherwise it targets that comment.
    entry = models.ForeignKey(
        HallOfFameEntry,
        on_delete=models.CASCADE,
        related_name='reactions',
    )
    comment = models.ForeignKey(
        HallOfFameComment,
        on_delete=models.CASCADE,
        related_name='reactions',
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='hall_of_fame_reactions',
        null=True,
        blank=True,
    )
    # target_key makes the uniqueness rule work for entry reactions even though
    # SQL NULL semantics would otherwise allow duplicate (comment=NULL) rows.
    target_key = models.CharField(max_length=32)
    # u:<id> for accounts, g:<HMAC> for an anonymous browser session.
    reactor_key = models.CharField(max_length=80)
    emoji = models.CharField(max_length=8, choices=Emoji.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('target_key', 'reactor_key', 'emoji'),
                name='hof_reaction_identity_uniq',
            ),
        ]
        indexes = [
            models.Index(fields=('target_key', 'emoji'), name='hof_reaction_target_idx'),
            models.Index(fields=('reactor_key', '-created_at'), name='hof_reaction_reactor_idx'),
        ]

    def __str__(self):
        return f'{self.emoji} {self.target_key} by {self.reactor_key[:16]}'


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
