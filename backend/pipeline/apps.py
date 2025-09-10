from django.apps import AppConfig

class PipelineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pipeline'
    
    def ready(self):
        # Import tasks to register them with Celery
        try:
            from . import tasks
        except ImportError:
            pass
