# celery.py - Celery Configuration for Pipeline Tasks

import os
from celery import Celery
from django.conf import settings
from celery.schedules import crontab

# Set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'transgrade.settings')

app = Celery('transgrade_pipeline')

# Load task modules from all registered Django apps
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Celery Beat Configuration for Periodic Tasks
app.conf.beat_schedule = {
    'monitor-pipeline-progress': {
        'task': 'pipeline.tasks.monitor_pipeline_progress',
        'schedule': crontab(minute='*/5'),  # Run every 5 minutes
    },
    'restart-workers-periodically': {
        'task': 'pipeline.tasks.start_pipeline_workers',
        'schedule': crontab(minute='*/10'),  # Run every 10 minutes
    },
}

app.conf.timezone = 'UTC'

# Additional Celery Configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    task_routes={
        'pipeline.tasks.ocr_worker': {'queue': 'ocr'},
        'pipeline.tasks.chunking_worker': {'queue': 'chunking'},
        'pipeline.tasks.qa_worker': {'queue': 'qa'},
        'pipeline.tasks.grading_worker': {'queue': 'grading'},
        'pipeline.tasks.process_pdf_stamps': {'queue': 'stamps'},
    }
)

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')