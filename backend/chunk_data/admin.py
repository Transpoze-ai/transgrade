# admin.py for chunk_data app
from django.contrib import admin
from .models import ChunkData
import json


@admin.register(ChunkData)
class ChunkDataAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'question_paper_uuid',
        'roll_no',
        'get_total_chunks',
        'get_total_pages',
        'created_at'
    ]
    list_filter = ['question_paper_uuid', 'created_at']
    search_fields = ['roll_no', 'question_paper_uuid']
    readonly_fields = ['id', 'created_at', 'updated_at', 'formatted_json']
    ordering = ['question_paper_uuid', 'roll_no']

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'question_paper_uuid', 'roll_no')
        }),
        ('Chunk Data', {
            'fields': ('chunk_data', 'formatted_json'),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def formatted_json(self, obj):
        """Display formatted JSON in admin"""
        if obj.chunk_data:
            return json.dumps(obj.chunk_data, indent=2)
        return "No JSON data"
    formatted_json.short_description = 'Formatted Chunk JSON'

    def has_change_permission(self, request, obj=None):
        """Allow change permission"""
        return True

    def has_delete_permission(self, request, obj=None):
        """Allow delete permission"""
        return True