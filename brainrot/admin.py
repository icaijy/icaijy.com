from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import HallOfFameEntry


@admin.register(HallOfFameEntry)
class HallOfFameEntryAdmin(admin.ModelAdmin):
    list_display = ('submitter', 'score', 'state', 'duration_seconds', 'created_at', 'review_video')
    list_filter = ('state', 'created_at')
    search_fields = ('user__username', 'display_name')
    list_editable = ('score', 'state')
    readonly_fields = ('user', 'mime_type', 'duration_seconds', 'event_timeline', 'created_at', 'review_video')
    actions = ('approve_entries', 'reject_entries')

    @admin.display(description='Submitter', ordering='user__username')
    def submitter(self, obj):
        return obj.public_name

    @admin.display(description='Recording')
    def review_video(self, obj):
        if not obj.pk:
            return 'Save first'
        video_url = f'/67/hall-of-fame/{obj.pk}/video/'
        return format_html(
            '<a href="{}" target="_blank">Open recording</a> · <a href="{}?download=1">Download</a>',
            video_url,
            video_url,
        )

    @admin.action(description='Approve selected entries')
    def approve_entries(self, request, queryset):
        queryset.update(state=HallOfFameEntry.State.APPROVED, reviewed_at=timezone.now())

    @admin.action(description='Reject selected entries')
    def reject_entries(self, request, queryset):
        queryset.update(state=HallOfFameEntry.State.REJECTED, reviewed_at=timezone.now())
