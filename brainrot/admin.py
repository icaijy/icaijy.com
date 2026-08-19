from django.contrib import admin
from django.utils.html import format_html

from .models import HallOfFameComment, HallOfFameEntry


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


@admin.register(HallOfFameComment)
class HallOfFameCommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'entry_link', 'short_body', 'is_submission_note', 'created_at')
    list_filter = ('is_submission_note', 'created_at', 'entry__game_mode')
    search_fields = ('author_name', 'user__username', 'body', 'entry__display_name', 'entry__user__username')
    readonly_fields = ('entry', 'user', 'author_name', 'body', 'client_key', 'is_submission_note', 'created_at')

    @admin.display(description='Author')
    def author(self, obj):
        return obj.public_name

    @admin.display(description='HOF entry')
    def entry_link(self, obj):
        return format_html('<a href="/67/hall-of-fame/{}/">#{} · {}</a>', obj.entry_id, obj.entry_id, obj.entry.public_name)

    @admin.display(description='Comment')
    def short_body(self, obj):
        return obj.body[:80]
