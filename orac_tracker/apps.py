import os
from django.apps import AppConfig

class OracTrackerConfig(AppConfig):
    name = 'orac_tracker'
    scheduler = None

    def ready(self):
        from apscheduler.schedulers.background import BackgroundScheduler
        from django_apscheduler.jobstores import DjangoJobStore
        from . import tasks

        if os.environ.get('RUN_MAIN', None) != 'true':
            return  # 避免 runserver 启动两次

        scheduler = BackgroundScheduler()
        scheduler.add_jobstore(DjangoJobStore(), "default")

        scheduler.add_job(
            tasks.autoupdate,
            'cron',
            hour=4,
            minute=0,
            timezone='Australia/Melbourne',
            id='daily_scraper_job',
            replace_existing = True
        )
        scheduler.start()
        OracTrackerConfig.scheduler = scheduler
