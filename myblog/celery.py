from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# 设置 Django 配置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myblog.settings')

app = Celery('myblog')

# 从 Django settings 中读取 CELERY 配置
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现各 app 下 tasks.py 中的任务
app.autodiscover_tasks()

