from django.db import migrations, models

import brainrot.storage
import vce.models


class Migration(migrations.Migration):
    dependencies = [('vce', '0003_algorithmicsrun_bank')]

    operations = [
        migrations.AddField(
            model_name='algorithmicsrun',
            name='video',
            field=models.FileField(blank=True, storage=brainrot.storage.private_media_storage, upload_to=vce.models.vce_run_upload_path),
        ),
        migrations.AddField(
            model_name='algorithmicsrun',
            name='video_mime_type',
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name='algorithmicsrun',
            name='video_duration_seconds',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
