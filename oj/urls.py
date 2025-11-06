from django.urls import path
from . import views

urlpatterns = [
    path('problem/<int:problem_id>/', views.problem_detail, name='problem_detail'),
    path('problem/<int:problem_id>/speedrun', views.problem_speedrun, name='problem_speedrun'),
    path('submission/<int:sub_id>/', views.submission_detail, name='submission_detail'),
    path('submission/<int:sub_id>/status/', views.submission_status, name='submission_status'),
    path('', views.problem_list, name='problem_list')
]

