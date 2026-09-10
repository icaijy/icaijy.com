from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="VCEAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("display_name", models.CharField(blank=True, max_length=32)),
                ("score", models.PositiveIntegerField(default=0)),
                ("wrong_count", models.PositiveIntegerField(default=0)),
                ("elapsed_ms", models.PositiveIntegerField(default=60000)),
                ("question_ids", models.JSONField(default=list)),
                ("answers", models.JSONField(default=list)),
                ("completed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="vce_speedruns",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-score", "wrong_count", "completed_at", "id"),
                "indexes": [
                    models.Index(fields=["-score", "wrong_count", "completed_at"], name="vce_hof_rank_idx"),
                    models.Index(fields=["user", "-completed_at"], name="vce_user_run_idx"),
                ],
            },
        ),
    ]
