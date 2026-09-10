from django.contrib import admin

from .models import AlgorithmicsRun


@admin.register(AlgorithmicsRun)
class AlgorithmicsRunAdmin(admin.ModelAdmin):
    list_display = ('public_name', 'score', 'is_submitted', 'started_at')
    list_filter = ('is_submitted', 'started_at')
    search_fields = ('display_name', 'user__username', 'token')
    readonly_fields = ('token', 'started_at', 'finished_at', 'question_ids', 'attempts')
