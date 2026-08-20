from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import (
    Cosmetic,
    CosmeticOffer,
    CurrencyBalance,
    CurrencyTransaction,
    DailySettlement,
    EquippedCosmetic,
    HallOfFameComment,
    HallOfFameEntry,
    HallOfFameReaction,
    UserCosmetic,
)


@admin.register(HallOfFameEntry)
class HallOfFameEntryAdmin(admin.ModelAdmin):
    list_display = ('submitter', 'game_mode', 'score', 'visibility', 'asset_value_67', 'duration_seconds', 'created_at', 'review_video')
    list_filter = ('game_mode', 'visibility', 'created_at')
    search_fields = ('user__username', 'display_name')
    list_editable = ('score', 'visibility')
    readonly_fields = (
        'user', 'mime_type', 'duration_seconds', 'event_timeline', 'metrics',
        'asset_value_67', 'asset_revision', 'created_at', 'review_video',
    )
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
        # Save one-by-one so HOF asset signals revalue each entry.
        for entry in queryset:
            entry.visibility = HallOfFameEntry.Visibility.PUBLIC
            entry.save(update_fields=['visibility'])

    @admin.action(description='Make selected entries private')
    def make_private(self, request, queryset):
        for entry in queryset:
            entry.visibility = HallOfFameEntry.Visibility.PRIVATE
            entry.save(update_fields=['visibility'])


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


@admin.register(HallOfFameReaction)
class HallOfFameReactionAdmin(admin.ModelAdmin):
    list_display = ('emoji', 'target_key', 'user', 'created_at')
    list_filter = ('emoji', 'created_at', 'entry__game_mode')
    search_fields = ('target_key', 'reactor_key', 'user__username', 'entry__user__username', 'entry__display_name')
    readonly_fields = ('entry', 'comment', 'user', 'target_key', 'reactor_key', 'emoji', 'created_at')


class CosmeticOfferInline(admin.TabularInline):
    model = CosmeticOffer
    extra = 1


@admin.register(Cosmetic)
class CosmeticAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'enabled', 'sort_order', 'preview')
    list_filter = ('category', 'enabled')
    list_editable = ('enabled', 'sort_order')
    search_fields = ('name', 'slug', 'description', 'badge_text')
    readonly_fields = ('preview',)
    inlines = (CosmeticOfferInline,)
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'category', 'description', 'enabled', 'sort_order')}),
        ('Appearance — admin is trusted, good luck', {'fields': ('css', 'extra_css', 'badge_text', 'image_url', 'preview')}),
    )

    @admin.display(description='Preview')
    def preview(self, obj):
        if not obj.pk:
            return 'Save once to preview.'
        selector = f'.admin-cosmetic-preview-{obj.pk}'
        extra = (obj.extra_css or '').replace('__SELECTOR__', selector).replace('__IMAGE_URL__', obj.image_url or '')
        text = obj.badge_text or ('icaijy' if obj.category == Cosmetic.Category.USERNAME else obj.name)
        if obj.category in {Cosmetic.Category.HOF, Cosmetic.Category.COMMENT}:
            body = f'<div class="admin-cosmetic-preview-{obj.pk}" style="padding:.65rem;border:1px solid #ddd;border-radius:.4rem"><strong>{text}</strong><br><small>Live admin CSS preview</small></div>'
        else:
            body = f'<span class="admin-cosmetic-preview-{obj.pk}" style="display:inline-block;padding:.35rem .65rem">{text}</span>'
        return mark_safe(f'<style>{selector}{{{obj.css or ""}}}{extra}</style>{body}')


@admin.register(CurrencyBalance)
class CurrencyBalanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'currency', 'balance', 'lifetime_earned', 'updated_at')
    list_filter = ('currency',)
    search_fields = ('user__username',)
    readonly_fields = ('user', 'currency', 'balance', 'lifetime_earned', 'updated_at')


@admin.register(CurrencyTransaction)
class CurrencyTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'currency', 'amount', 'reason', 'created_at')
    list_filter = ('currency', 'reason', 'created_at')
    search_fields = ('user__username', 'unique_key', 'reason')
    readonly_fields = ('user', 'currency', 'amount', 'reason', 'unique_key', 'hall_entry', 'metadata', 'created_at')


@admin.register(UserCosmetic)
class UserCosmeticAdmin(admin.ModelAdmin):
    list_display = ('user', 'cosmetic', 'expires_at', 'acquired_at')
    list_filter = ('cosmetic__category', 'cosmetic')
    search_fields = ('user__username', 'cosmetic__name')
    readonly_fields = ('acquired_at',)


@admin.register(EquippedCosmetic)
class EquippedCosmeticAdmin(admin.ModelAdmin):
    list_display = ('user', 'category', 'cosmetic', 'updated_at')
    list_filter = ('category',)
    search_fields = ('user__username', 'cosmetic__name')
    readonly_fields = ('updated_at',)


@admin.register(DailySettlement)
class DailySettlementAdmin(admin.ModelAdmin):
    list_display = ('date', 'participant_count', 'distributed', 'settled_at')
    readonly_fields = ('date', 'participant_count', 'distributed', 'settled_at')
