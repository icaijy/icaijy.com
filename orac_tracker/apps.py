from django.apps import AppConfig

class OracTrackerConfig(AppConfig):
    name = 'orac_tracker'
    scheduler = None

    def ready(self):
        # 仅注册 scheduler，不 start（避免数据库操作）
        from apscheduler.schedulers.background import BackgroundScheduler
        from django_apscheduler.jobstores import DjangoJobStore
        from . import tasks

        scheduler = BackgroundScheduler()
        scheduler.add_jobstore(DjangoJobStore(), "default")
        scheduler.add_job(
            tasks.autoupdate,
            'cron',
            hour=4,
            minute=0,
            timezone='Australia/Melbourne',
            id='daily_scraper_job'
        )

        OracTrackerConfig.scheduler = scheduler
