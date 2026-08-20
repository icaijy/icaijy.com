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
        COMBINE = 'combine', _('67 × Tung Tung Combine')
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
    score = models.PositiveIntegerField()
    video = models.FileField(
        upload_to=hall_of_fame_upload_path,
        storage=private_media_storage,
    )
    mime_type = models.CharField(max_length=32)
    duration_seconds = models.FloatField()
    event_timeline = models.JSONField(default=list, blank=True)
    metrics = models.JSONField(default=dict, blank=True)
    visibility = models.CharField(
        max_length=12,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )
    # Cached contribution of this HOF entry to the owner's 67 Coin balance.
    # It is revalued whenever score/visibility changes and removed on deletion.
    asset_value_67 = models.PositiveIntegerField(default=0)
    asset_revision = models.PositiveIntegerField(default=0)
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

    @property
    def combo_six_seven(self):
        return int((self.metrics or {}).get('six_seven', 0) or 0)

    @property
    def combo_leg_claps(self):
        return int((self.metrics or {}).get('leg_claps', 0) or 0)


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
    author_name = models.CharField(max_length=32)
    body = models.TextField()
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
    target_key = models.CharField(max_length=32)
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


class CurrencyTransaction(models.Model):
    class Currency(models.TextChoices):
        SIXTY_ONE = '61', '61 Coin'
        SIXTY_SEVEN = '67', '67 Coin'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='brainrot_currency_transactions')
    currency = models.CharField(max_length=2, choices=Currency.choices)
    amount = models.BigIntegerField()
    reason = models.CharField(max_length=100)
    unique_key = models.CharField(max_length=180, unique=True)
    hall_entry = models.ForeignKey(HallOfFameEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name='currency_transactions')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at', '-id')
        indexes = [models.Index(fields=('user', 'currency', '-created_at'), name='coin_user_currency_idx')]

    def __str__(self):
        sign = '+' if self.amount >= 0 else ''
        return f'{self.user}: {sign}{self.amount} {self.currency} ({self.reason})'


class CurrencyBalance(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='brainrot_currency_balances')
    currency = models.CharField(max_length=2, choices=CurrencyTransaction.Currency.choices)
    balance = models.BigIntegerField(default=0)
    lifetime_earned = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('user', 'currency'), name='currency_balance_user_uniq')]
        indexes = [models.Index(fields=('currency', '-balance'), name='currency_wealth_rank_idx')]

    def __str__(self):
        return f'{self.user}: {self.balance} {self.currency}'


class Cosmetic(models.Model):
    class Category(models.TextChoices):
        USERNAME = 'username', 'Username'
        HOF = 'hof', 'HOF background'
        BADGE = 'badge', 'Badge'
        COMMENT = 'comment', 'Comment'

    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80, unique=True)
    category = models.CharField(max_length=16, choices=Category.choices)
    description = models.CharField(max_length=300, blank=True)
    css = models.TextField(blank=True, help_text='Raw CSS declarations applied to this cosmetic element.')
    extra_css = models.TextField(blank=True, help_text='Optional full CSS. Use __SELECTOR__ for this cosmetic selector and __IMAGE_URL__ for image_url.')
    badge_text = models.CharField(max_length=40, blank=True)
    image_url = models.URLField(blank=True)
    enabled = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        ordering = ('category', 'sort_order', 'name')

    def __str__(self):
        return f'{self.name} ({self.get_category_display()})'


class CosmeticOffer(models.Model):
    cosmetic = models.ForeignKey(Cosmetic, on_delete=models.CASCADE, related_name='offers')
    currency = models.CharField(max_length=2, choices=CurrencyTransaction.Currency.choices, default=CurrencyTransaction.Currency.SIXTY_SEVEN)
    price = models.PositiveIntegerField()
    duration_days = models.PositiveIntegerField(null=True, blank=True, help_text='Blank means permanent.')
    enabled = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        ordering = ('sort_order', 'price', 'id')

    def __str__(self):
        duration = 'permanent' if self.duration_days is None else f'{self.duration_days}d'
        return f'{self.cosmetic.name}: {self.price} {self.currency} ({duration})'


class UserCosmetic(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='brainrot_cosmetics')
    cosmetic = models.ForeignKey(Cosmetic, on_delete=models.CASCADE, related_name='owners')
    expires_at = models.DateTimeField(null=True, blank=True)
    acquired_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('user', 'cosmetic'), name='user_cosmetic_uniq')]

    def __str__(self):
        return f'{self.user}: {self.cosmetic}'


class EquippedCosmetic(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='brainrot_equipped_cosmetics')
    category = models.CharField(max_length=16, choices=Cosmetic.Category.choices)
    cosmetic = models.ForeignKey(Cosmetic, on_delete=models.CASCADE, related_name='equipped_by')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('user', 'category'), name='equipped_cosmetic_category_uniq')]

    def __str__(self):
        return f'{self.user}: {self.category} = {self.cosmetic}'


class DailySettlement(models.Model):
    date = models.DateField(unique=True)
    settled_at = models.DateTimeField(auto_now_add=True)
    participant_count = models.PositiveIntegerField(default=0)
    distributed = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('-date',)

    def __str__(self):
        return f'{self.date}: {self.distributed} 61 Coin'
