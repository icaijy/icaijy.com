from django.db import models


class BattleSeason(models.Model):
    slug = models.SlugField(max_length=61, unique=True)
    title = models.CharField(max_length=200)
    version = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)
    played_at = models.CharField(max_length=50, blank=True)
    rules_markdown = models.TextField()
    viewer_html = models.TextField()
    # Includes original judge, C++ adapter, rules, bot sources and all replays.
    original_archive = models.BinaryField()
    leaderboard = models.JSONField(default=list)
    participants = models.JSONField(default=list)
    bot_sources = models.JSONField(default=dict)
    seed_list = models.JSONField(default=list)
    metadata = models.JSONField(default=dict)
    is_public = models.BooleanField(default=True)

    class Meta:
        ordering = ('-created_at', '-id')

    def __str__(self):
        return self.title


class BattleMatch(models.Model):
    season = models.ForeignKey(BattleSeason, on_delete=models.CASCADE, related_name='matches')
    index = models.PositiveIntegerField()
    seed = models.BigIntegerField()
    blue = models.CharField(max_length=61)
    red = models.CharField(max_length=61)
    score_blue = models.FloatField()
    score_red = models.FloatField()
    winner = models.SmallIntegerField(null=True, blank=True)
    summary = models.JSONField()
    replay = models.JSONField()

    class Meta:
        ordering = ('index',)
        constraints = [models.UniqueConstraint(fields=['season','index'], name='battle_season_match_unique')]

    def __str__(self):
        return f'{self.season.slug} #{self.index}: {self.blue} vs {self.red}'
