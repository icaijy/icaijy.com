from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('manual_update/', views.manual_update, name='ot_manual_update'),
]
