from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('actions-status/', views.actions_status, name='orac_actions_status'),
    path('history/', views.history, name='orac_history'),
    path('manual_update/', views.manual_update, name='ot_manual_update'),
]
