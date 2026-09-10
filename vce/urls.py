from django.urls import path

from . import views

app_name = "vce"

urlpatterns = [
    path("", views.index, name="index"),
    path("start/", views.start_run, name="start"),
    path("answer/", views.answer_question, name="answer"),
    path("finish/", views.finish_run, name="finish"),
    path("attempt/<int:attempt_id>/", views.attempt_detail, name="attempt_detail"),
]
