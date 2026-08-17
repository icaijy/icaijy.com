from django.db import migrations, models


def migrate_visibility(apps, schema_editor):
    entry = apps.get_model('brainrot', 'HallOfFameEntry')
    entry.objects.filter(visibility='approved').update(visibility='public')
    entry.objects.exclude(visibility='public').update(visibility='private')


def restore_review_state(apps, schema_editor):
    entry = apps.get_model('brainrot', 'HallOfFameEntry')
    entry.objects.filter(visibility='public').update(visibility='approved')
    entry.objects.exclude(visibility='approved').update(visibility='pending')


class Migration(migrations.Migration):

    dependencies = [
        ('brainrot', '0003_anonymous_hall_of_fame'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='halloffameentry',
            name='hof_public_rank_idx',
        ),
        migrations.RenameField(
            model_name='halloffameentry',
            old_name='state',
            new_name='visibility',
        ),
        migrations.RunPython(migrate_visibility, restore_review_state),
        migrations.AlterField(
            model_name='halloffameentry',
            name='visibility',
            field=models.CharField(
                choices=[('public', 'Public'), ('private', 'Private')],
                default='private',
                max_length=12,
            ),
        ),
        migrations.RemoveField(
            model_name='halloffameentry',
            name='reviewed_at',
        ),
        migrations.AddIndex(
            model_name='halloffameentry',
            index=models.Index(
                fields=['visibility', '-score', 'created_at'],
                name='hof_public_rank_idx',
            ),
        ),
    ]
