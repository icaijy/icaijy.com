from django.urls import path
from django.views.generic import RedirectView
from django.views.i18n import JavaScriptCatalog

from . import comment_views, download_views, economy_views, views, voice_views

app_name = 'brainrot'

urlpatterns = [
    path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript_catalog'),
    path('', views.index, name='index'),
    path('counter/', views.counter, name='counter'),
    path('voice/', voice_views.voice_counter, name='voice_counter'),
    path('games/', RedirectView.as_view(pattern_name='brainrot:index', permanent=True), name='games_legacy'),
    path('submit/', views.submit_hall_of_fame, name='submit_hall_of_fame'),

    path('daily/', economy_views.daily, name='daily'),
    path('wealth/', economy_views.wealth, name='wealth'),
    path('shop/', economy_views.shop, name='shop'),
    path('inventory/', economy_views.inventory, name='inventory'),
    path('shop/buy/<int:offer_id>/', economy_views.buy_cosmetic, name='buy_cosmetic'),
    path('shop/equip/<int:cosmetic_id>/', economy_views.equip, name='equip_cosmetic'),
    path('shop/unequip/<str:category>/', economy_views.unequip, name='unequip_cosmetic'),
    path('cosmetics.css', economy_views.cosmetics_css, name='cosmetics_css'),

    path('hall-of-fame/', views.hall_of_fame, name='hall_of_fame'),
    path('hall-of-fame/mine/', views.my_hall_of_fame, name='my_hall_of_fame'),
    path('hall-of-fame/<int:entry_id>/', views.hall_of_fame_detail, name='hall_of_fame_detail'),
    path('hall-of-fame/<int:entry_id>/video/', download_views.hall_of_fame_video, name='hall_of_fame_video'),
    path('hall-of-fame/<int:entry_id>/comments/', comment_views.add_comment, name='add_comment'),
    path('hall-of-fame/<int:entry_id>/visibility/', views.set_hall_of_fame_visibility, name='set_hall_of_fame_visibility'),
    path('hall-of-fame/<int:entry_id>/delete/', views.delete_hall_of_fame_entry, name='delete_hall_of_fame_entry'),
    path('comments/preview/', comment_views.preview_comment, name='comment_preview'),
    path('comments/<int:comment_id>/delete/', comment_views.delete_comment, name='delete_comment'),
    path('reactions/toggle/', comment_views.toggle_reaction, name='toggle_reaction'),
    path('challenge/<int:entry_id>/', voice_views.challenge_dispatch, name='challenge'),
    path('typing/', views.typing_test, name='typing_test'),
]
