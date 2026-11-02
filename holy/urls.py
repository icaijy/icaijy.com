from django.urls import path
from . import views

app_name = 'holy'
urlpatterns = [
    path('', views.index, name='index'),
    path('query/', views.compare, name='compare'),
    path('status/', views.status, name='status'),
]
