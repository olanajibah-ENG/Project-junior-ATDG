from django.apps import AppConfig


class CoreAiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core_ai'

    def ready(self):
        # Import Celery tasks here to ensure they are registered
        from .analyze import analyze_code  # noqa