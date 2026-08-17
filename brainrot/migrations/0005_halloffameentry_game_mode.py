from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('brainrot', '0004_hall_of_fame_visibility'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='halloffameentry',
            name='hof_public_rank_idx',
        ),
        migrations.AddField(
            model_name='halloffameentry',
            name='game_mode',
            field=models.CharField(
                choices=[
                    ('six_seven', '67 Counter'),
                    ('leg_claps', 'Tung Tung Leg Claps'),
                ],
                default='six_seven',
                max_length=16,
            ),
        ),
        migrations.AddIndex(
            model_name='halloffameentry',
            index=models.Index(
                fields=['game_mode', 'visibility', '-score', 'created_at'],
                name='hof_mode_public_rank_idx',
            ),
        ),
    ]
