from django.urls import path

from . import views

app_name = 'brainrot'

urlpatterns = [
    path('', views.index, name='index'),
    path('67/', views.counter, name='counter'),
    path('67/submit/', views.submit_hall_of_fame, name='submit_hall_of_fame'),
    path('67/hall-of-fame/', views.hall_of_fame, name='hall_of_fame'),
    path('67/hall-of-fame/<int:entry_id>/video/', views.hall_of_fame_video, name='hall_of_fame_video'),
    path('typing/', views.typing_test, name='typing_test'),
]
