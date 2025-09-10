from django.contrib import admin
from .models import AnswerScript
from .utils import delete_s3_folder


@admin.register(AnswerScript)
class AnswerScriptAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'question_paper_uuid', 
        'roll_no', 
        'get_image_count', 
        'created_at'
    ]
    list_filter = ['question_paper_uuid', 'created_at']
    search_fields = ['roll_no', 'question_paper_uuid']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['question_paper_uuid', 'roll_no']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'question_paper_uuid', 'roll_no')
        }),
        ('Images', {
            'fields': ('image_urls',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_image_count(self, obj):
        return obj.get_image_count()
    get_image_count.short_description = 'Image Count'
    get_image_count.admin_order_field = 'image_urls'
    
    def delete_model(self, request, obj):
        """Delete single object and its S3 folder"""
        folder_path = obj.get_s3_folder_path()
        delete_s3_folder(folder_path)
        super().delete_model(request, obj)
    
    def delete_queryset(self, request, queryset):
        """Delete multiple objects and their S3 folders"""
        for obj in queryset:
            folder_path = obj.get_s3_folder_path()
            delete_s3_folder(folder_path)
        super().delete_queryset(request, queryset)
    
    def has_change_permission(self, request, obj=None):
        """Allow change permission"""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Allow delete permission"""
        return True