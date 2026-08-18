from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('brainrot', '0005_halloffameentry_game_mode'),
    ]

    operations = [
        migrations.AlterField(
            model_name='halloffameentry',
            name='game_mode',
            field=models.CharField(
                choices=[
                    ('six_seven', '67 Counter'),
                    ('leg_claps', 'Tung Tung Leg Claps'),
                    ('voice_67', 'Six Seven Voice Speedrun'),
                ],
                default='six_seven',
                max_length=16,
            ),
        ),
    ]
