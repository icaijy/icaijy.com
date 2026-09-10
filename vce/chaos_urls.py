from django.urls import path

from . import views

app_name = 'vce_chaos'

urlpatterns = [
    path('', views.chaos_index, name='index'),
    path('<slug:bank_id>/', views.chaos_play, name='play'),
]
