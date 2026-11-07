# Generated for Mini Battlecode database archive, Django 5.2 compatible.
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='BattleSeason',
            fields=[
                ('id',models.BigAutoField(primary_key=True, serialize=False)),
                ('slug',models.SlugField(max_length=61,unique=True)),
                ('title',models.CharField(max_length=200)),
                ('version',models.CharField(max_length=80)),
                ('created_at',models.DateTimeField(auto_now_add=True)),
                ('played_at',models.CharField(blank=True,max_length=50)),
                ('rules_markdown',models.TextField()),
                ('viewer_html',models.TextField()),
                ('original_archive',models.BinaryField()),
                ('leaderboard',models.JSONField(default=list)),
                ('participants',models.JSONField(default=list)),
                ('bot_sources',models.JSONField(default=dict)),
                ('seed_list',models.JSONField(default=list)),
                ('metadata',models.JSONField(default=dict)),
                ('is_public',models.BooleanField(default=True)),
            ],
            options={'ordering': ('-created_at','-id')},
        ),
        migrations.CreateModel(
            name='BattleMatch',
            fields=[
                ('id',models.BigAutoField(primary_key=True, serialize=False)),
                ('index',models.PositiveIntegerField()),
                ('seed',models.BigIntegerField()),
                ('blue',models.CharField(max_length=61)),
                ('red',models.CharField(max_length=61)),
                ('score_blue',models.FloatField()),
                ('score_red',models.FloatField()),
                ('winner',models.SmallIntegerField(blank=True,null=True)),
                ('summary',models.JSONField()),
                ('replay',models.JSONField()),
                ('season',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='matches',to='battlecode_archive.battleseason')),
            ],
            options={'ordering': ('index',)},
        ),
        migrations.AddConstraint(model_name='battlematch',constraint=models.UniqueConstraint(fields=('season','index'),name='battle_season_match_unique')),
    ]
