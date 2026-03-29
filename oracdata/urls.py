from django.urls import path
from . import views

urlpatterns = [
    path('oracdata/', views.analytics, name='analytics'),
]
