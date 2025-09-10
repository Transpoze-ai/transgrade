# pipeline/management/commands/cleanup_old_logs.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from pipeline.models import ProcessingLog

class Command(BaseCommand):
    help = 'Clean up old processing logs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete logs older than this many days (default: 30)'
        )

    def handle(self, *args, **options):
        days = options['days']
        cutoff_date = timezone.now() - timedelta(days=days)
        
        old_logs = ProcessingLog.objects.filter(timestamp__lt=cutoff_date)
        count = old_logs.count()
        old_logs.delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'Deleted {count} logs older than {days} days')
        )