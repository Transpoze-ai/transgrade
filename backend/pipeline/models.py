# pipeline/models.py - Roll Number Based Pipeline Models

from django.db import models
from django.utils import timezone
import json

class PipelineJob(models.Model):
    """Main job tracking for PDF processing"""
    STATUS_CHOICES = [
        ('initiated', 'Job Initiated'),
        ('stamp_processing', 'Processing Stamps'),
        ('students_discovered', 'Students Discovered'),
        ('pipeline_active', 'Pipeline Active'),
        ('completed', 'All Students Completed'),
        ('failed', 'Job Failed'),
    ]
    
    job_id = models.CharField(max_length=255, unique=True)
    question_paper_uuid = models.CharField(max_length=255)
    pdf_file_path = models.CharField(max_length=500, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated')
    
    # Discovery results
    discovered_roll_numbers = models.JSONField(default=list)  # ['1', '2', '3', '4', '5']
    total_students = models.IntegerField(default=0)
    
    # Progress tracking
    students_completed = models.IntegerField(default=0)
    students_failed = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    stamp_started_at = models.DateTimeField(null=True, blank=True)
    stamp_completed_at = models.DateTimeField(null=True, blank=True)
    pipeline_started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    error_message = models.TextField(null=True, blank=True)
    
    def get_completion_rate(self):
        if self.total_students > 0:
            return round((self.students_completed / self.total_students) * 100, 1)
        return 0

    def __str__(self):
        return f"Job {self.job_id} - {self.status}"


class StudentQueue(models.Model):
    """Queue system for individual students by roll number"""
    STAGE_CHOICES = [
        ('discovered', 'Student Discovered'),
        ('ocr_pending', 'OCR Pending'),
        ('ocr_processing', 'OCR Processing'),
        ('ocr_completed', 'OCR Completed'),
        ('chunking_pending', 'Chunking Pending'),
        ('chunking_processing', 'Chunking Processing'),
        ('chunking_completed', 'Chunking Completed'),
        ('qa_pending', 'QA Mapping Pending'),
        ('qa_processing', 'QA Mapping Processing'),
        ('qa_completed', 'QA Mapping Completed'),
        ('grading_pending', 'Grading Pending'),
        ('grading_processing', 'Grading Processing'),
        ('grading_completed', 'Grading Completed'),
        ('failed', 'Processing Failed'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    # Core identifiers - Roll number is primary after stamp detection
    pipeline_job = models.ForeignKey(PipelineJob, on_delete=models.CASCADE, related_name='student_queues')
    question_paper_uuid = models.CharField(max_length=255)
    roll_no = models.CharField(max_length=50)  # Primary identifier for queue
    
    # Current pipeline state
    current_stage = models.CharField(max_length=30, choices=STAGE_CHOICES, default='discovered')
    overall_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Stage-specific status tracking
    ocr_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    chunking_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    qa_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    grading_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Timestamps for each stage
    created_at = models.DateTimeField(auto_now_add=True)
    ocr_started_at = models.DateTimeField(null=True, blank=True)
    ocr_completed_at = models.DateTimeField(null=True, blank=True)
    chunking_started_at = models.DateTimeField(null=True, blank=True)
    chunking_completed_at = models.DateTimeField(null=True, blank=True)
    qa_started_at = models.DateTimeField(null=True, blank=True)
    qa_completed_at = models.DateTimeField(null=True, blank=True)
    grading_started_at = models.DateTimeField(null=True, blank=True)
    grading_completed_at = models.DateTimeField(null=True, blank=True)
    
    # Error handling
    error_message = models.TextField(null=True, blank=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    
    # Queue priority (higher number = higher priority)
    priority = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['question_paper_uuid', 'roll_no']
        ordering = ['-priority', 'created_at']  # Process high priority first, then FIFO
    
    def __str__(self):
        return f"Roll {self.roll_no} - {self.current_stage}"
    
    def get_progress_percentage(self):
        """Calculate completion percentage"""
        stages = ['ocr', 'chunking', 'qa', 'grading']
        completed_stages = sum(1 for stage in stages if getattr(self, f"{stage}_status") == 'completed')
        return round((completed_stages / len(stages)) * 100, 1)


class ProcessingLog(models.Model):
    """Detailed logging for each student's processing"""
    # Make student_queue nullable for existing data, but required for new entries
    student_queue = models.ForeignKey(
        StudentQueue, 
        on_delete=models.CASCADE, 
        related_name='logs',
        null=True,  # Allow null for existing records
        blank=True
    )
    stage = models.CharField(max_length=30)
    status = models.CharField(max_length=20)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    processing_duration = models.FloatField(null=True, blank=True)  # seconds
    
    # Add these fields to maintain compatibility with existing data
    roll_no = models.CharField(max_length=50, null=True, blank=True)  # Fallback identifier
    question_paper_uuid = models.CharField(max_length=255, null=True, blank=True)  # Fallback identifier
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        if self.student_queue:
            return f"Roll {self.student_queue.roll_no} - {self.stage} - {self.status}"
        elif self.roll_no:
            return f"Roll {self.roll_no} - {self.stage} - {self.status}"
        else:
            return f"{self.stage} - {self.status}"


class PipelineMetrics(models.Model):
    question_paper_uuid = models.CharField(max_length=255, unique=True)
    total_students = models.IntegerField(default=0)
    completed_students = models.IntegerField(default=0)
    failed_students = models.IntegerField(default=0)
    avg_total_time = models.FloatField(default=0.0)  # in seconds
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Metrics for {self.question_paper_uuid}"