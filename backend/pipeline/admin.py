from django.contrib import admin
from django.utils.html import format_html
from .models import StudentQueue, ProcessingLog, PipelineMetrics, PipelineJob


@admin.register(PipelineJob)
class PipelineJobAdmin(admin.ModelAdmin):
    list_display = [
        'job_id', 'question_paper_uuid', 'status', 'total_students',
        'students_completed', 'students_failed', 'completion_rate_display', 'created_at'
    ]
    
    list_filter = ['status', 'created_at']
    search_fields = ['job_id', 'question_paper_uuid']
    readonly_fields = [
        'created_at', 'stamp_started_at', 'stamp_completed_at',
        'pipeline_started_at', 'completed_at'
    ]
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('job_id', 'question_paper_uuid', 'pdf_file_path')
        }),
        ('Status & Progress', {
            'fields': ('status', 'total_students', 'students_completed', 'students_failed')
        }),
        ('Discovery Results', {
            'fields': ('discovered_roll_numbers',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                ('created_at', 'stamp_started_at'),
                ('stamp_completed_at', 'pipeline_started_at'),
                ('completed_at',)
            ),
            'classes': ('collapse',)
        }),
        ('Error Handling', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        })
    )
    
    def completion_rate_display(self, obj):
        return f"{obj.get_completion_rate()}%"
    completion_rate_display.short_description = 'Completion Rate'


@admin.register(StudentQueue)
class StudentQueueAdmin(admin.ModelAdmin):
    list_display = [
        'roll_no', 'question_paper_uuid', 'current_stage', 'overall_status',
        'ocr_status', 'chunking_status', 'qa_status', 'grading_status',
        'created_at', 'progress_bar'
    ]
    
    list_filter = [
        'overall_status', 'current_stage', 'ocr_status', 'chunking_status',
        'qa_status', 'grading_status', 'created_at'
    ]
    
    search_fields = ['question_paper_uuid', 'roll_no', 'pipeline_job__job_id']
    
    readonly_fields = [
        'created_at', 'ocr_started_at', 'ocr_completed_at',
        'chunking_started_at', 'chunking_completed_at', 'qa_started_at',
        'qa_completed_at', 'grading_started_at', 'grading_completed_at'
    ]
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('pipeline_job', 'question_paper_uuid', 'roll_no')
        }),
        ('Status', {
            'fields': ('current_stage', 'overall_status', 'priority')
        }),
        ('Stage Status', {
            'fields': (
                'ocr_status', 'chunking_status', 'qa_status', 'grading_status'
            )
        }),
        ('Timestamps', {
            'fields': (
                ('created_at', 'ocr_started_at', 'ocr_completed_at'),
                ('chunking_started_at', 'chunking_completed_at'),
                ('qa_started_at', 'qa_completed_at'),
                ('grading_started_at', 'grading_completed_at')
            ),
            'classes': ('collapse',)
        }),
        ('Error Handling', {
            'fields': ('error_message', 'retry_count', 'max_retries'),
            'classes': ('collapse',)
        })
    )
    
    def progress_bar(self, obj):
        stages = ['ocr', 'chunking', 'qa', 'grading']
        completed = sum(1 for stage in stages if getattr(obj, f"{stage}_status") == 'completed')
        progress = (completed / len(stages)) * 100
        
        return format_html(
            '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
            '<div style="width: {}%; height: 20px; background-color: #28a745; border-radius: 3px; text-align: center; color: white; font-size: 12px; line-height: 20px;">'
            '{}%</div></div>',
            progress, int(progress)
        )
    progress_bar.short_description = 'Progress'

    actions = ['retry_failed_students', 'reset_students']
    
    def retry_failed_students(self, request, queryset):
        failed_students = queryset.filter(overall_status='failed')
        count = 0
        
        for student in failed_students:
            # Reset to appropriate stage
            if student.ocr_status == 'failed':
                student.current_stage = 'ocr_pending'
                student.ocr_status = 'pending'
            elif student.chunking_status == 'failed':
                student.current_stage = 'chunking_pending'
                student.chunking_status = 'pending'
            elif student.qa_status == 'failed':
                student.current_stage = 'qa_pending'
                student.qa_status = 'pending'
            elif student.grading_status == 'failed':
                student.current_stage = 'grading_pending'
                student.grading_status = 'pending'
            
            student.overall_status = 'pending'
            student.retry_count = 0
            student.error_message = None
            student.save()
            count += 1
        
        self.message_user(request, f'Successfully reset {count} failed students for retry.')
    retry_failed_students.short_description = 'Retry failed students'


@admin.register(ProcessingLog)
class ProcessingLogAdmin(admin.ModelAdmin):
    list_display = ['student_queue', 'stage', 'status', 'timestamp', 'message_preview']
    list_filter = ['stage', 'status', 'timestamp']
    search_fields = ['student_queue__roll_no', 'student_queue__question_paper_uuid', 'message']
    readonly_fields = ['timestamp']
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'


@admin.register(PipelineMetrics)
class PipelineMetricsAdmin(admin.ModelAdmin):
    list_display = [
        'question_paper_uuid', 'total_students', 'completed_students',
        'failed_students', 'completion_rate', 'avg_total_time_minutes'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    def completion_rate(self, obj):
        if obj.total_students > 0:
            rate = (obj.completed_students / obj.total_students) * 100
            return f"{rate:.1f}%"
        return "0%"
    completion_rate.short_description = 'Completion Rate'
    
    def avg_total_time_minutes(self, obj):
        return f"{obj.avg_total_time / 60:.1f} min"
    avg_total_time_minutes.short_description = 'Avg Total Time'