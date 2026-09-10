from django.contrib import admin

from .models import VCEAttempt


@admin.register(VCEAttempt)
class VCEAttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "public_name", "score", "wrong_count", "completed_at")
    list_filter = ("completed_at",)
    search_fields = ("user__username", "display_name")
    readonly_fields = (
        "user",
        "display_name",
        "score",
        "wrong_count",
        "elapsed_ms",
        "question_ids",
        "answers",
        "completed_at",
    )

    @admin.display(description="Player")
    def public_name(self, obj):
        return obj.public_name
