from django.contrib import admin
from .models import BattleSeason, BattleMatch

@admin.register(BattleSeason)
class BattleSeasonAdmin(admin.ModelAdmin):
    list_display = ('slug','title','version','is_public','created_at')
    list_filter = ('is_public',)
    search_fields = ('slug','title')
    fields = ('slug', 'title', 'version', 'played_at', 'is_public')

    def has_add_permission(self, request):
        return False

@admin.register(BattleMatch)
class BattleMatchAdmin(admin.ModelAdmin):
    list_display = ('season','index','blue','red','score_blue','score_red','winner')
    list_filter = ('season',)
    search_fields = ('blue','red')
    fields = ('season', 'index', 'blue', 'red', 'score_blue', 'score_red', 'winner')

    def has_add_permission(self, request):
        return False
