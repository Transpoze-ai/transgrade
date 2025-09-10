from django.contrib import admin
from .models import OCRData
import json


@admin.register(OCRData)
class OCRDataAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'question_paper_uuid',
        'roll_no',
        'page_number',
        'get_text_preview',
        'get_confidence_score',
        'created_at'
    ]
    list_filter = ['question_paper_uuid', 'page_number', 'created_at']
    search_fields = ['roll_no', 'question_paper_uuid']
    readonly_fields = ['id', 'created_at', 'updated_at', 'formatted_json']
    ordering = ['question_paper_uuid', 'roll_no', 'page_number']

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'question_paper_uuid', 'roll_no', 'page_number')
        }),
        ('OCR Data', {
            'fields': ('ocr_json_dump', 'formatted_json'),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_text_preview(self, obj):
        """Show first 50 characters of extracted text"""
        text = obj.get_text_content()
        return text[:50] + "..." if len(text) > 50 else text
    get_text_preview.short_description = 'Text Preview'

    def formatted_json(self, obj):
        """Display formatted JSON in admin"""
        if obj.ocr_json_dump:
            return json.dumps(obj.ocr_json_dump, indent=2)
        return "No JSON data"
    formatted_json.short_description = 'Formatted OCR JSON'

    def has_change_permission(self, request, obj=None):
        """Allow change permission"""
        return True

    def has_delete_permission(self, request, obj=None):
        """Allow delete permission"""
        return True