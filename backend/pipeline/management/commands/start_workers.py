# pipeline/management/commands/start_workers.py
from django.core.management.base import BaseCommand
from pipeline.tasks import start_pipeline_workers

class Command(BaseCommand):
    help = 'Start all pipeline workers'

    def handle(self, *args, **options):
        self.stdout.write('Starting pipeline workers...')
        start_pipeline_workers.delay()
        self.stdout.write(
            self.style.SUCCESS('Pipeline workers started successfully')
        )