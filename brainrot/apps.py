from django.apps import AppConfig


class BrainrotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'brainrot'

    def ready(self):
        from . import signals  # noqa: F401
