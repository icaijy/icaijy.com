from django.urls import path

from . import views

app_name = 'vce'

urlpatterns = [
    path('', views.index, name='index'),
    path('play/<slug:bank_id>/', views.play, name='play'),
    path('api/prepare/', views.prepare_run, name='prepare'),
    path('api/start/', views.start_run, name='start'),
    path('api/refill/', views.refill_run, name='refill'),
    path('api/answer/', views.answer, name='answer'),
    path('api/finish/', views.finish_run, name='finish'),
    path('run/<uuid:token>/', views.run_detail, name='run_detail'),
    path('run/<uuid:token>/video/', views.run_video, name='run_video'),
]
