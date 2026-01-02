# Optional Celery import - only if available
try:
    from .celery_app import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    # Celery not installed, skip import
    pass