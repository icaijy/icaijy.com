from django.urls import path

from . import views

app_name = 'vce'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/start/', views.start_run, name='start'),
    path('api/answer/', views.answer, name='answer'),
    path('api/finish/', views.finish_run, name='finish'),
    path('run/<uuid:token>/', views.run_detail, name='run_detail'),
]
