# pipeline/management/commands/reset_failed_students.py
from django.core.management.base import BaseCommand
from pipeline.models import StudentQueue, ProcessingLog

class Command(BaseCommand):
    help = 'Reset all failed students to retry'

    def add_arguments(self, parser):
        parser.add_argument(
            '--job-id',
            type=str,
            help='Reset only students from specific job'
        )

    def handle(self, *args, **options):
        job_id = options.get('job_id')
        
        if job_id:
            failed_students = StudentQueue.objects.filter(
                pipeline_job__job_id=job_id,
                overall_status='failed'
            )
        else:
            failed_students = StudentQueue.objects.filter(overall_status='failed')
        
        count = 0
        for student in failed_students:
            # Reset to appropriate stage
            if student.grading_status == 'failed':
                student.grading_status = 'pending'
                student.current_stage = 'grading_pending'
            elif student.qa_status == 'failed':
                student.qa_status = 'pending'
                student.current_stage = 'qa_pending'
            elif student.chunking_status == 'failed':
                student.chunking_status = 'pending'
                student.current_stage = 'chunking_pending'
            elif student.ocr_status == 'failed':
                student.ocr_status = 'pending'
                student.current_stage = 'ocr_pending'
            
            student.overall_status = 'pending'
            student.retry_count = 0
            student.error_message = None
            student.save()
            
            ProcessingLog.objects.create(
                student_queue=student,
                stage='reset',
                status='initiated',
                message=f"Reset failed student {student.roll_no} via management command"
            )
            count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Reset {count} failed students')
        )