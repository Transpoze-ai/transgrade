from django.contrib import admin
from .models import QAData
import json


@admin.register(QAData)
class QADataAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'question_paper_uuid',
        'roll_no',
        'get_answered_count',
        'get_parsing_errors',
        'has_vlm_data',
        'has_vlm_restructured_data',
        'total_questions_processed',
        'processing_timestamp',
        'created_at'
    ]
    list_filter = [
        'question_paper_uuid', 
        'total_questions_processed', 
        'processing_timestamp',
        'created_at'
    ]
    search_fields = ['roll_no', 'question_paper_uuid']
    readonly_fields = [
        'id', 
        'created_at', 
        'updated_at', 
        'formatted_qa_mapping',
        'formatted_vlm_json',
        'formatted_vlm_restructured_json'
    ]
    ordering = ['question_paper_uuid', 'roll_no']

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'question_paper_uuid', 'roll_no')
        }),
        ('QA Mapping Data', {
            'fields': ('qa_mapping', 'formatted_qa_mapping'),
            'classes': ('wide',)
        }),
        ('VLM Data', {
            'fields': ('vlm_json', 'formatted_vlm_json'),
            'classes': ('wide', 'collapse')
        }),
        ('VLM Restructured Data', {
            'fields': ('vlm_restructured_json', 'formatted_vlm_restructured_json'),
            'classes': ('wide', 'collapse')
        }),
        ('Processing Information', {
            'fields': ('total_questions_processed', 'processing_timestamp')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_answered_count(self, obj):
        """Show count of answered questions"""
        return obj.get_answered_questions_count()
    get_answered_count.short_description = 'Answered'

    def get_parsing_errors(self, obj):
        """Show count of parsing errors"""
        return obj.get_parsing_errors_count()
    get_parsing_errors.short_description = 'Parsing Errors'

    def has_vlm_data(self, obj):
        """Show if VLM data exists"""
        return obj.has_vlm_data()
    has_vlm_data.short_description = 'Has VLM Data'
    has_vlm_data.boolean = True

    def has_vlm_restructured_data(self, obj):
        """Show if VLM restructured data exists"""
        return obj.has_vlm_restructured_data()
    has_vlm_restructured_data.short_description = 'Has VLM Restructured'
    has_vlm_restructured_data.boolean = True

    def formatted_qa_mapping(self, obj):
        """Display formatted QA mapping JSON in admin"""
        if obj.qa_mapping:
            return json.dumps(obj.qa_mapping, indent=2)
        return "No QA mapping data"
    formatted_qa_mapping.short_description = 'Formatted QA Mapping'

    def formatted_vlm_json(self, obj):
        """Display formatted VLM JSON in admin"""
        if obj.vlm_json:
            return json.dumps(obj.vlm_json, indent=2)
        return "No VLM data"
    formatted_vlm_json.short_description = 'Formatted VLM JSON'

    def formatted_vlm_restructured_json(self, obj):
        """Display formatted VLM restructured JSON in admin"""
        if obj.vlm_restructured_json:
            return json.dumps(obj.vlm_restructured_json, indent=2)
        return "No VLM restructured data"
    formatted_vlm_restructured_json.short_description = 'Formatted VLM Restructured JSON'

    def has_change_permission(self, request, obj=None):
        """Allow change permission"""
        return True

    def has_delete_permission(self, request, obj=None):
        """Allow delete permission"""
        return True