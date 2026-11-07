from django.urls import path
from . import views

app_name = 'battlecode_archive'
urlpatterns = [
    path('', views.index, name='index'),
    path('<slug:slug>/', views.detail, name='detail'),
    path('<slug:slug>/viewer/', views.viewer, name='viewer'),
    path('<slug:slug>/match/<int:index>/', views.match_detail, name='match'),
    path('<slug:slug>/match/<int:index>/replay.json', views.replay, name='replay'),
]
