from django.db import migrations, models


def copy_existing_scores(apps, schema_editor):
    Run = apps.get_model('vce', 'AlgorithmicsRun')
    for run in Run.objects.all().iterator():
        run.final_score = run.score
        run.save(update_fields=('final_score',))


class Migration(migrations.Migration):
    dependencies = [('vce', '0001_initial')]

    operations = [
        migrations.AlterModelOptions(name='algorithmicsrun', options={'ordering': ('-final_score', 'finished_at', 'id')}),
        migrations.RemoveIndex(model_name='algorithmicsrun', name='vce_run_score_idx'),
        migrations.AddField(model_name='algorithmicsrun', name='game_mode', field=models.CharField(choices=[('normal', 'Serious'), ('six_seven', '67'), ('leg_claps', 'Tung Tung'), ('combine', 'Combine')], default='normal', max_length=16)),
        migrations.AddField(model_name='algorithmicsrun', name='movement_score', field=models.PositiveIntegerField(default=1)),
        migrations.AddField(model_name='algorithmicsrun', name='final_score', field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='algorithmicsrun', name='metrics', field=models.JSONField(default=dict)),
        migrations.RunPython(copy_existing_scores, migrations.RunPython.noop),
        migrations.AddIndex(model_name='algorithmicsrun', index=models.Index(fields=['game_mode', '-final_score', 'finished_at'], name='vce_mode_score_idx')),
    ]
