from django.contrib import admin

from .models import AlgorithmicsRun


@admin.register(AlgorithmicsRun)
class AlgorithmicsRunAdmin(admin.ModelAdmin):
    list_display = ('public_name', 'bank_id', 'game_mode', 'final_score', 'score', 'is_submitted', 'started_at')
    list_filter = ('bank_id', 'game_mode', 'is_submitted', 'started_at')
    search_fields = ('display_name', 'user__username', 'token')
    readonly_fields = ('token', 'started_at', 'finished_at', 'question_ids', 'attempts')
