from django.urls import path
from . import views

urlpatterns = [
    path('orac-leaderboard/', views.index, name='index'),
    path('manual_update/', views.manual_update, name='ot_manual_update'),
]
