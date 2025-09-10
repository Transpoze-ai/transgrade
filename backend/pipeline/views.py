# pipeline/views.py - API Endpoints for Pipeline Management

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db import models
from django.db.models import Q, Sum
from .models import PipelineJob, StudentQueue, ProcessingLog
from .tasks import process_pdf_stamps, start_pipeline_workers
import uuid
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
def start_pdf_pipeline(request):
    """
    Start complete pipeline from PDF upload
    
    Expected payload:
    {
        "job_id": "exam_batch_001",  # optional, will generate if not provided
        "question_paper_uuid": "44e13dca-17cc-4e75-93ea-82aa9e8d74ec",
        "pdf_file_path": "/path/to/uploaded.pdf"  # optional
    }
    """
    try:
        job_id = request.data.get('job_id') or f"job_{uuid.uuid4().hex[:8]}"
        question_paper_uuid = request.data.get('question_paper_uuid')
        pdf_file_path = request.data.get('pdf_file_path')
        
        if not question_paper_uuid:
            return Response({
                "error": "question_paper_uuid is required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if job already exists
        if PipelineJob.objects.filter(job_id=job_id).exists():
            return Response({
                "error": f"Job with ID {job_id} already exists"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create pipeline job
        job = PipelineJob.objects.create(
            job_id=job_id,
            question_paper_uuid=question_paper_uuid,
            pdf_file_path=pdf_file_path,
            status='initiated'
        )
        
        logger.info(f"Created pipeline job: {job_id} for UUID: {question_paper_uuid}")
        
        # Start stamp processing
        process_pdf_stamps.delay(job_id, question_paper_uuid, pdf_file_path)
        
        return Response({
            "message": "PDF pipeline started successfully",
            "job_id": job_id,
            "question_paper_uuid": question_paper_uuid,
            "status": "initiated"
        })
    
    except Exception as e:
        logger.error(f"Failed to start pipeline: {str(e)}")
        return Response({
            "error": f"Failed to start pipeline: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def job_status(request, job_id):
    """Get complete job status"""
    try:
        job = PipelineJob.objects.get(job_id=job_id)
        students = StudentQueue.objects.filter(pipeline_job=job)
        
        # Calculate stage statistics
        stage_stats = {}
        stages = ['ocr', 'chunking', 'qa', 'grading']
        
        for stage in stages:
            stage_stats[stage] = {
                'pending': students.filter(**{f"{stage}_status": 'pending'}).count(),
                'processing': students.filter(**{f"{stage}_status": 'processing'}).count(),
                'completed': students.filter(**{f"{stage}_status": 'completed'}).count(),
                'failed': students.filter(**{f"{stage}_status": 'failed'}).count()
            }
        
        # Currently processing students
        current_processing = []
        for stage in stages:
            processing_student = students.filter(**{f"{stage}_status": 'processing'}).first()
            if processing_student:
                current_processing.append({
                    'stage': stage,
                    'roll_no': processing_student.roll_no,
                    'started_at': getattr(processing_student, f"{stage}_started_at")
                })
        
        return Response({
            "job_id": job_id,
            "question_paper_uuid": job.question_paper_uuid,
            "status": job.status,
            "total_students": job.total_students,
            "students_completed": job.students_completed,
            "students_failed": job.students_failed,
            "completion_rate": job.get_completion_rate(),
            "discovered_roll_numbers": job.discovered_roll_numbers,
            "stage_statistics": stage_stats,
            "currently_processing": current_processing,
            "created_at": job.created_at,
            "last_updated": timezone.now()
        })
    
    except PipelineJob.DoesNotExist:
        return Response({
            "error": "Job not found"
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def student_status(request, question_paper_uuid, roll_no):
    """Get detailed status for specific student"""
    try:
        student = StudentQueue.objects.get(
            question_paper_uuid=question_paper_uuid,
            roll_no=roll_no
        )
        
        # Get recent logs
        recent_logs = ProcessingLog.objects.filter(student_queue=student)[:10]
        
        logs_data = [{
            "stage": log.stage,
            "status": log.status,
            "message": log.message,
            "timestamp": log.timestamp,
            "duration": log.processing_duration
        } for log in recent_logs]
        
        return Response({
            "roll_no": student.roll_no,
            "question_paper_uuid": student.question_paper_uuid,
            "current_stage": student.current_stage,
            "overall_status": student.overall_status,
            "progress_percentage": student.get_progress_percentage(),
            "stage_status": {
                "ocr": student.ocr_status,
                "chunking": student.chunking_status,
                "qa": student.qa_status,
                "grading": student.grading_status
            },
            "timestamps": {
                "created_at": student.created_at,
                "ocr_started": student.ocr_started_at,
                "ocr_completed": student.ocr_completed_at,
                "chunking_started": student.chunking_started_at,
                "chunking_completed": student.chunking_completed_at,
                "qa_started": student.qa_started_at,
                "qa_completed": student.qa_completed_at,
                "grading_started": student.grading_started_at,
                "grading_completed": student.grading_completed_at
            },
            "error_info": {
                "error_message": student.error_message,
                "retry_count": student.retry_count,
                "max_retries": student.max_retries
            },
            "recent_logs": logs_data
        })
    
    except StudentQueue.DoesNotExist:
        return Response({
            "error": "Student not found in pipeline"
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def pipeline_dashboard(request):
    """Get overall pipeline dashboard data"""
    try:
        # Active jobs
        active_jobs = PipelineJob.objects.filter(
            status__in=['initiated', 'stamp_processing', 'students_discovered', 'pipeline_active']
        )
        
        # Recent completed jobs
        completed_jobs = PipelineJob.objects.filter(status='completed').order_by('-completed_at')[:5]
        
        # Overall statistics
        total_jobs = PipelineJob.objects.count()
        total_students_processed = PipelineJob.objects.filter(status='completed').aggregate(
            total=Sum('students_completed')
        )['total'] or 0
        
        # Current queue status across all active jobs
        queue_stats = {
            'ocr_pending': StudentQueue.objects.filter(current_stage='ocr_pending').count(),
            'ocr_processing': StudentQueue.objects.filter(current_stage='ocr_processing').count(),
            'chunking_pending': StudentQueue.objects.filter(current_stage='chunking_pending').count(),
            'chunking_processing': StudentQueue.objects.filter(current_stage='chunking_processing').count(),
            'qa_pending': StudentQueue.objects.filter(current_stage='qa_pending').count(),
            'qa_processing': StudentQueue.objects.filter(current_stage='qa_processing').count(),
            'grading_pending': StudentQueue.objects.filter(current_stage='grading_pending').count(),
            'grading_processing': StudentQueue.objects.filter(current_stage='grading_processing').count(),
            'completed': StudentQueue.objects.filter(overall_status='completed').count(),
            'failed': StudentQueue.objects.filter(overall_status='failed').count()
        }
        
        active_jobs_data = [{
            "job_id": job.job_id,
            "question_paper_uuid": job.question_paper_uuid,
            "status": job.status,
            "total_students": job.total_students,
            "completion_rate": job.get_completion_rate(),
            "created_at": job.created_at
        } for job in active_jobs]
        
        return Response({
            "active_jobs": active_jobs_data,
            "completed_jobs": [{
                "job_id": job.job_id,
                "completion_rate": job.get_completion_rate(),
                "completed_at": job.completed_at,
                "total_students": job.total_students
            } for job in completed_jobs],
            "overall_stats": {
                "total_jobs": total_jobs,
                "total_students_processed": total_students_processed,
                "active_jobs_count": active_jobs.count()
            },
            "queue_statistics": queue_stats,
            "timestamp": timezone.now()
        })
    
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        return Response({
            "error": f"Failed to load dashboard: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def retry_failed_student(request, question_paper_uuid, roll_no):
    """Retry processing for a failed student"""
    try:
        student = StudentQueue.objects.get(
            question_paper_uuid=question_paper_uuid,
            roll_no=roll_no
        )
        
        if student.overall_status != 'failed':
            return Response({
                "error": "Student is not in failed state"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Reset student to appropriate pending state based on last successful stage
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
        else:
            # Start from beginning
            student.current_stage = 'ocr_pending'
        
        student.overall_status = 'pending'
        student.retry_count = 0
        student.error_message = None
        student.save()
        
        ProcessingLog.objects.create(
            student_queue=student,
            stage='retry',
            status='initiated',
            message=f"Manual retry initiated for roll {roll_no}"
        )
        
        # Restart workers
        start_pipeline_workers.delay()
        
        return Response({
            "message": f"Student {roll_no} retry initiated successfully",
            "current_stage": student.current_stage,
            "status": student.overall_status
        })
    
    except StudentQueue.DoesNotExist:
        return Response({
            "error": "Student not found"
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def restart_pipeline_workers(request):
    """Manually restart all pipeline workers"""
    try:
        start_pipeline_workers.delay()
        
        return Response({
            "message": "Pipeline workers restarted successfully",
            "timestamp": timezone.now()
        })
    
    except Exception as e:
        logger.error(f"Failed to restart workers: {str(e)}")
        return Response({
            "error": f"Failed to restart workers: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def queue_status(request):
    """Get current queue status across all stages"""
    try:
        # Students waiting in each queue
        queues = {
            'ocr_queue': list(StudentQueue.objects.filter(
                current_stage='ocr_pending'
            ).values('roll_no', 'question_paper_uuid', 'created_at')),
            
            'chunking_queue': list(StudentQueue.objects.filter(
                current_stage='chunking_pending'
            ).values('roll_no', 'question_paper_uuid', 'created_at')),
            
            'qa_queue': list(StudentQueue.objects.filter(
                current_stage='qa_pending'
            ).values('roll_no', 'question_paper_uuid', 'created_at')),
            
            'grading_queue': list(StudentQueue.objects.filter(
                current_stage='grading_pending'
            ).values('roll_no', 'question_paper_uuid', 'created_at'))
        }
        
        # Currently processing
        processing = {
            'ocr_processing': list(StudentQueue.objects.filter(
                current_stage='ocr_processing'
            ).values('roll_no', 'question_paper_uuid', 'ocr_started_at')),
            
            'chunking_processing': list(StudentQueue.objects.filter(
                current_stage='chunking_processing'
            ).values('roll_no', 'question_paper_uuid', 'chunking_started_at')),
            
            'qa_processing': list(StudentQueue.objects.filter(
                current_stage='qa_processing'
            ).values('roll_no', 'question_paper_uuid', 'qa_started_at')),
            
            'grading_processing': list(StudentQueue.objects.filter(
                current_stage='grading_processing'
            ).values('roll_no', 'question_paper_uuid', 'grading_started_at'))
        }
        
        return Response({
            "pending_queues": queues,
            "currently_processing": processing,
            "queue_lengths": {k: len(v) for k, v in queues.items()},
            "processing_counts": {k: len(v) for k, v in processing.items()},
            "timestamp": timezone.now()
        })
    
    except Exception as e:
        logger.error(f"Queue status error: {str(e)}")
        return Response({
            "error": f"Failed to get queue status: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)