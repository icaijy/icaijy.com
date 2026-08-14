from django.conf import settings
from django.urls import path
from . import views

if settings.OJ_ENABLED:
    urlpatterns = [
        path('problem/<int:problem_id>/', views.problem_detail, name='problem_detail'),
        path('problem/<int:problem_id>/speedrun', views.problem_speedrun, name='problem_speedrun'),
        path('problem/<int:problem_id>/leaderboard/', views.problem_leaderboard, name='problem_leaderboard'),
        path('submission/<int:sub_id>/', views.submission_detail, name='submission_detail'),
        path('submission/<int:sub_id>/status/', views.submission_status, name='submission_status'),
        path('', views.problem_list, name='problem_list'),
    ]
else:
    # Catch every historical URL, including POST submission URLs, before any
    # problem lookup or submission creation can happen.
    urlpatterns = [
        path('', views.retired, name='problem_list'),
        path('<path:legacy_path>', views.retired, name='oj_retired'),
    ]
