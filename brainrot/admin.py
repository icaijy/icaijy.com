from django.contrib import admin
from django.utils.html import format_html

from .models import HallOfFameEntry


@admin.register(HallOfFameEntry)
class HallOfFameEntryAdmin(admin.ModelAdmin):
    list_display = ('submitter', 'game_mode', 'score', 'visibility', 'duration_seconds', 'created_at', 'review_video')
    list_filter = ('game_mode', 'visibility', 'created_at')
    search_fields = ('user__username', 'display_name')
    list_editable = ('score', 'visibility')
    readonly_fields = ('user', 'mime_type', 'duration_seconds', 'event_timeline', 'created_at', 'review_video')
    actions = ('make_public', 'make_private')

    @admin.display(description='Submitter', ordering='user__username')
    def submitter(self, obj):
        return obj.public_name

    @admin.display(description='Recording')
    def review_video(self, obj):
        if not obj.pk:
            return 'Save first'
        video_url = f'/67/hall-of-fame/{obj.pk}/video/'
        return format_html(
            '<a href="{}" target="_blank">Open recording</a> · <a href="{}?download=1&amp;format=mp4">Download MP4</a>',
            video_url,
            video_url,
        )

    @admin.action(description='Make selected entries public')
    def make_public(self, request, queryset):
        queryset.update(visibility=HallOfFameEntry.Visibility.PUBLIC)

    @admin.action(description='Make selected entries private')
    def make_private(self, request, queryset):
        queryset.update(visibility=HallOfFameEntry.Visibility.PRIVATE)
