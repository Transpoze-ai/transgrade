# pipeline/management/commands/pipeline_status.py
from django.core.management.base import BaseCommand
from pipeline.models import PipelineJob, StudentQueue

class Command(BaseCommand):
    help = 'Show pipeline status'

    def handle(self, *args, **options):
        active_jobs = PipelineJob.objects.filter(
            status__in=['initiated', 'stamp_processing', 'students_discovered', 'pipeline_active']
        ).count()
        
        queue_counts = {
            'OCR Pending': StudentQueue.objects.filter(current_stage='ocr_pending').count(),
            'OCR Processing': StudentQueue.objects.filter(current_stage='ocr_processing').count(),
            'Chunking Pending': StudentQueue.objects.filter(current_stage='chunking_pending').count(),
            'Chunking Processing': StudentQueue.objects.filter(current_stage='chunking_processing').count(),
            'QA Pending': StudentQueue.objects.filter(current_stage='qa_pending').count(),
            'QA Processing': StudentQueue.objects.filter(current_stage='qa_processing').count(),
            'Grading Pending': StudentQueue.objects.filter(current_stage='grading_pending').count(),
            'Grading Processing': StudentQueue.objects.filter(current_stage='grading_processing').count(),
            'Completed': StudentQueue.objects.filter(overall_status='completed').count(),
            'Failed': StudentQueue.objects.filter(overall_status='failed').count(),
        }
        
        self.stdout.write(f"\nActive Jobs: {active_jobs}")
        self.stdout.write("\nQueue Status:")
        for stage, count in queue_counts.items():
            self.stdout.write(f"  {stage}: {count}")