from rest_framework import serializers
from .models import QAData


class QADataSerializer(serializers.ModelSerializer):
    questions_count = serializers.SerializerMethodField(read_only=True)
    answered_count = serializers.SerializerMethodField(read_only=True)
    parsing_errors_count = serializers.SerializerMethodField(read_only=True)
    vlm_items_count = serializers.SerializerMethodField(read_only=True)
    vlm_restructured_items_count = serializers.SerializerMethodField(read_only=True)
    has_vlm_data = serializers.SerializerMethodField(read_only=True)
    has_vlm_restructured_data = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = QAData
        fields = [
            'id',
            'question_paper_uuid',
            'roll_no',
            'qa_mapping',
            'vlm_json',
            'vlm_restructured_json',
            'total_questions_processed',
            'processing_timestamp',
            'questions_count',
            'answered_count',
            'parsing_errors_count',
            'vlm_items_count',
            'vlm_restructured_items_count',
            'has_vlm_data',
            'has_vlm_restructured_data',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_questions_count(self, obj):
        return obj.get_questions_count()

    def get_answered_count(self, obj):
        return obj.get_answered_questions_count()

    def get_parsing_errors_count(self, obj):
        return obj.get_parsing_errors_count()

    def get_vlm_items_count(self, obj):
        return obj.get_vlm_items_count()

    def get_vlm_restructured_items_count(self, obj):
        return obj.get_vlm_restructured_items_count()

    def get_has_vlm_data(self, obj):
        return obj.has_vlm_data()

    def get_has_vlm_restructured_data(self, obj):
        return obj.has_vlm_restructured_data()

    def validate(self, data):
        """
        Check that roll_no and question_paper_uuid combination is unique for new instances
        """
        if self.instance is None:  # Creating new instance
            roll_no = data.get('roll_no')
            question_paper_uuid = data.get('question_paper_uuid')

            if QAData.objects.filter(
                roll_no=roll_no,
                question_paper_uuid=question_paper_uuid
            ).exists():
                raise serializers.ValidationError(
                    "QA data for this roll number and question paper UUID already exists"
                )
        return data

    def validate_qa_mapping(self, value):
        if not isinstance(value, dict) and not isinstance(value, list):
            raise serializers.ValidationError("QA mapping must be a valid JSON object or list")
        return value

    def validate_vlm_json(self, value):
        if value is not None and not isinstance(value, dict) and not isinstance(value, list):
            raise serializers.ValidationError("VLM JSON must be a valid JSON object or list")
        return value

    def validate_vlm_restructured_json(self, value):
        if value is not None and not isinstance(value, dict) and not isinstance(value, list):
            raise serializers.ValidationError("VLM restructured JSON must be a valid JSON object or list")
        return value


class QADataListSerializer(serializers.ModelSerializer):
    questions_count = serializers.SerializerMethodField()
    answered_count = serializers.SerializerMethodField()
    parsing_errors_count = serializers.SerializerMethodField()
    has_vlm_data = serializers.SerializerMethodField()
    has_vlm_restructured_data = serializers.SerializerMethodField()

    class Meta:
        model = QAData
        fields = [
            'id',
            'question_paper_uuid',
            'roll_no',
            'total_questions_processed',
            'questions_count',
            'answered_count',
            'parsing_errors_count',
            'has_vlm_data',
            'has_vlm_restructured_data',
            'processing_timestamp',
            'created_at'
        ]

    def get_questions_count(self, obj):
        return obj.get_questions_count()

    def get_answered_count(self, obj):
        return obj.get_answered_questions_count()

    def get_parsing_errors_count(self, obj):
        return obj.get_parsing_errors_count()

    def get_has_vlm_data(self, obj):
        return obj.has_vlm_data()

    def get_has_vlm_restructured_data(self, obj):
        return obj.has_vlm_restructured_data()


class QADataByUUIDSerializer(serializers.ModelSerializer):
    questions_count = serializers.SerializerMethodField()
    answered_count = serializers.SerializerMethodField()
    parsing_errors_count = serializers.SerializerMethodField()
    has_vlm_data = serializers.SerializerMethodField()
    has_vlm_restructured_data = serializers.SerializerMethodField()

    class Meta:
        model = QAData
        fields = [
            'id',
            'roll_no',
            'total_questions_processed',
            'questions_count',
            'answered_count',
            'parsing_errors_count',
            'has_vlm_data',
            'has_vlm_restructured_data',
            'processing_timestamp',
            'created_at'
        ]

    def get_questions_count(self, obj):
        return obj.get_questions_count()

    def get_answered_count(self, obj):
        return obj.get_answered_questions_count()

    def get_parsing_errors_count(self, obj):
        return obj.get_parsing_errors_count()

    def get_has_vlm_data(self, obj):
        return obj.has_vlm_data()

    def get_has_vlm_restructured_data(self, obj):
        return obj.has_vlm_restructured_data()


class QADataProcessSerializer(serializers.Serializer):
    """Serializer for processing QA JSON data"""
    data = serializers.DictField()
    success = serializers.BooleanField(required=False)

    def validate_data(self, value):
        """Validate data structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Data must be a dictionary")
        
        # Check required fields
        required_fields = ['question_paper_uuid', 'roll_no', 'qa_mapping']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Missing required field: {field}")
        
        # Validate qa_mapping
        if not isinstance(value['qa_mapping'], list):
            raise serializers.ValidationError("qa_mapping must be a list")
                
        return value


# New serializers for VLM operations
class VLMDataSerializer(serializers.ModelSerializer):
    """Serializer specifically for VLM data operations"""
    class Meta:
        model = QAData
        fields = [
            'id',
            'question_paper_uuid',
            'roll_no',
            'vlm_json',
            'vlm_restructured_json',
            'updated_at'
        ]
        read_only_fields = ['id', 'question_paper_uuid', 'roll_no', 'updated_at']

    def validate_vlm_json(self, value):
        if value is not None and not isinstance(value, dict) and not isinstance(value, list):
            raise serializers.ValidationError("VLM JSON must be a valid JSON object or list")
        return value

    def validate_vlm_restructured_json(self, value):
        if value is not None and not isinstance(value, dict) and not isinstance(value, list):
            raise serializers.ValidationError("VLM restructured JSON must be a valid JSON object or list")
        return value
