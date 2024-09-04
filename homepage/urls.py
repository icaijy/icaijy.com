from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # 主页的 URL 路由
]