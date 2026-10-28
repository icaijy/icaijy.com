from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('history/', views.history, name='orac_history'),
    path('manual_update/', views.manual_update, name='ot_manual_update'),
]
