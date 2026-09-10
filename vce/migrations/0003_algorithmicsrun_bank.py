from django.db import migrations, models


TABLE = 'vce_algorithmicsrun'
OLD_INDEX = models.Index(
    fields=['game_mode', '-final_score', 'finished_at'],
    name='vce_mode_score_idx',
)
NEW_INDEX = models.Index(
    fields=['bank_id', 'game_mode', '-final_score'],
    name='vce_bank_score_idx',
)


def _columns(schema_editor):
    with schema_editor.connection.cursor() as cursor:
        return {
            column.name
            for column in schema_editor.connection.introspection.get_table_description(cursor, TABLE)
        }


def _constraints(schema_editor):
    with schema_editor.connection.cursor() as cursor:
        return schema_editor.connection.introspection.get_constraints(cursor, TABLE)


def add_bank_column_if_missing(apps, schema_editor):
    if 'bank_id' in _columns(schema_editor):
        return
    Run = apps.get_model('vce', 'AlgorithmicsRun')
    field = models.CharField(default='algorithmics_u34', max_length=48)
    field.set_attributes_from_name('bank_id')
    schema_editor.add_field(Run, field)


def remove_bank_column_if_present(apps, schema_editor):
    if 'bank_id' not in _columns(schema_editor):
        return
    Run = apps.get_model('vce', 'AlgorithmicsRun')
    schema_editor.remove_field(Run, Run._meta.get_field('bank_id'))


def replace_score_index(apps, schema_editor):
    Run = apps.get_model('vce', 'AlgorithmicsRun')
    constraints = _constraints(schema_editor)
    if OLD_INDEX.name in constraints:
        schema_editor.remove_index(Run, OLD_INDEX)
    if NEW_INDEX.name not in constraints:
        schema_editor.add_index(Run, NEW_INDEX)


def restore_score_index(apps, schema_editor):
    Run = apps.get_model('vce', 'AlgorithmicsRun')
    constraints = _constraints(schema_editor)
    if NEW_INDEX.name in constraints:
        schema_editor.remove_index(Run, NEW_INDEX)
    if OLD_INDEX.name not in constraints:
        schema_editor.add_index(Run, OLD_INDEX)


class Migration(migrations.Migration):
    dependencies = [('vce', '0002_algorithmicsrun_game_modes')]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(add_bank_column_if_missing, remove_bank_column_if_present),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='algorithmicsrun',
                    name='bank_id',
                    field=models.CharField(default='algorithmics_u34', max_length=48),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(replace_score_index, restore_score_index),
            ],
            state_operations=[
                migrations.RemoveIndex(
                    model_name='algorithmicsrun',
                    name='vce_mode_score_idx',
                ),
                migrations.AddIndex(
                    model_name='algorithmicsrun',
                    index=NEW_INDEX,
                ),
            ],
        ),
    ]
