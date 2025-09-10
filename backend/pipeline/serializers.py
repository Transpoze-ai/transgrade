from rest_framework import serializers
from .models import PipelineJob, StudentQueue, ProcessingLog, PipelineMetrics

class PipelineJobSerializer(serializers.ModelSerializer):
    completion_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = PipelineJob
        fields = '__all__'
    
    def get_completion_rate(self, obj):
        return obj.get_completion_rate()


class StudentQueueSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentQueue
        fields = '__all__'
    
    def get_progress_percentage(self, obj):
        return obj.get_progress_percentage()


class ProcessingLogSerializer(serializers.ModelSerializer):
    student_roll_no = serializers.SerializerMethodField()
    
    class Meta:
        model = ProcessingLog
        fields = '__all__'
    
    def get_student_roll_no(self, obj):
        return obj.student_queue.roll_no


class PipelineMetricsSerializer(serializers.ModelSerializer):
    completion_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = PipelineMetrics
        fields = '__all__'
    
    def get_completion_rate(self, obj):
        if obj.total_students > 0:
            return round((obj.completed_students / obj.total_students) * 100, 1)
        return 0