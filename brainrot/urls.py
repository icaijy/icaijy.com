from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = 'brainrot'

urlpatterns = [
    path('', views.index, name='index'),
    path('counter/', views.counter, name='counter'),
    path('games/', RedirectView.as_view(pattern_name='brainrot:index', permanent=True), name='games_legacy'),
    path('submit/', views.submit_hall_of_fame, name='submit_hall_of_fame'),
    path('hall-of-fame/', views.hall_of_fame, name='hall_of_fame'),
    path('hall-of-fame/<int:entry_id>/video/', views.hall_of_fame_video, name='hall_of_fame_video'),
    path('typing/', views.typing_test, name='typing_test'),
]
