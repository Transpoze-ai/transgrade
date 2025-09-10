# ============================================================================
# qp_data/admin.py
# ============================================================================

from django.contrib import admin
from .models import QPData
import json


@admin.register(QPData)
class QPDataAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'question_paper_uuid',
        'get_ocr_summary',
        'get_rubric_summary',
        'get_reference_summary',
        'get_vlm_summary',
        'is_complete',
        'created_at'
    ]
    list_filter = ['created_at', 'updated_at']
    search_fields = ['question_paper_uuid']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 
        'formatted_ocr_json', 'formatted_rubric_json', 
        'formatted_reference_json', 'formatted_vlm_json'
    ]
    ordering = ['-created_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'question_paper_uuid')
        }),
        ('JSON Data', {
            'fields': (
                'ocr_json', 'formatted_ocr_json', 
                'rubric_json', 'formatted_rubric_json', 
                'reference_json', 'formatted_reference_json',
                'vlm_json', 'formatted_vlm_json'
            ),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_ocr_summary(self, obj):
        return obj.get_ocr_summary()
    get_ocr_summary.short_description = 'OCR Summary'

    def get_rubric_summary(self, obj):
        return obj.get_rubric_summary()
    get_rubric_summary.short_description = 'Rubric Summary'

    def get_reference_summary(self, obj):
        return obj.get_reference_summary()
    get_reference_summary.short_description = 'Reference Summary'

    def get_vlm_summary(self, obj):
        return obj.get_vlm_summary()
    get_vlm_summary.short_description = 'VLM Summary'

    def formatted_ocr_json(self, obj):
        """Display formatted OCR JSON in admin"""
        if obj.ocr_json:
            return json.dumps(obj.ocr_json, indent=2)
        return "No OCR JSON data"
    formatted_ocr_json.short_description = 'Formatted OCR JSON'

    def formatted_rubric_json(self, obj):
        """Display formatted Rubric JSON in admin"""
        if obj.rubric_json:
            return json.dumps(obj.rubric_json, indent=2)
        return "No Rubric JSON data"
    formatted_rubric_json.short_description = 'Formatted Rubric JSON'

    def formatted_reference_json(self, obj):
        """Display formatted Reference JSON in admin"""
        if obj.reference_json:
            return json.dumps(obj.reference_json, indent=2)
        return "No Reference JSON data"
    formatted_reference_json.short_description = 'Formatted Reference JSON'

    def formatted_vlm_json(self, obj):
        """Display formatted VLM JSON in admin"""
        if obj.vlm_json:
            return json.dumps(obj.vlm_json, indent=2)
        return "No VLM JSON data"
    formatted_vlm_json.short_description = 'Formatted VLM JSON'

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True