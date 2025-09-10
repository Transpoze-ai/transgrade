# ============================================================================
# qp_data/serializers.py
# ============================================================================

from rest_framework import serializers
from .models import QPData
from .rubric_processor import RubricProcessor


class QPDataSerializer(serializers.ModelSerializer):
    ocr_summary = serializers.SerializerMethodField(read_only=True)
    rubric_summary = serializers.SerializerMethodField(read_only=True)
    reference_summary = serializers.SerializerMethodField(read_only=True)
    vlm_summary = serializers.SerializerMethodField(read_only=True)
    has_ocr_data = serializers.SerializerMethodField(read_only=True)
    has_rubric_data = serializers.SerializerMethodField(read_only=True)
    has_reference_data = serializers.SerializerMethodField(read_only=True)
    has_vlm_data = serializers.SerializerMethodField(read_only=True)
    is_complete = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = QPData
        fields = [
            'id',
            'question_paper_uuid',
            'ocr_json',
            'rubric_json',
            'reference_json',
            'vlm_json',
            'ocr_summary',
            'rubric_summary',
            'reference_summary',
            'vlm_summary',
            'has_ocr_data',
            'has_rubric_data',
            'has_reference_data',
            'has_vlm_data',
            'is_complete',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_ocr_summary(self, obj):
        return obj.get_ocr_summary()

    def get_rubric_summary(self, obj):
        return obj.get_rubric_summary()

    def get_reference_summary(self, obj):
        return obj.get_reference_summary()

    def get_vlm_summary(self, obj):
        return obj.get_vlm_summary()

    def get_has_ocr_data(self, obj):
        return obj.has_ocr_data()

    def get_has_rubric_data(self, obj):
        return obj.has_rubric_data()

    def get_has_reference_data(self, obj):
        return obj.has_reference_data()

    def get_has_vlm_data(self, obj):
        return obj.has_vlm_data()

    def get_is_complete(self, obj):
        return obj.is_complete()

    def validate_ocr_json(self, value):
        """Validate OCR JSON"""
        if value is not None and not isinstance(value, (dict, list)):
            raise serializers.ValidationError("OCR JSON must be a valid JSON object or array")
        return value

    def validate_rubric_json(self, value):
        """Validate Rubric JSON"""
        if value is not None and not isinstance(value, (dict, list)):
            raise serializers.ValidationError("Rubric JSON must be a valid JSON object or array")
        return value

    def validate_reference_json(self, value):
        """Validate Reference JSON"""
        if value is not None and not isinstance(value, (dict, list)):
            raise serializers.ValidationError("Reference JSON must be a valid JSON object or array")
        return value

    def validate_vlm_json(self, value):
        """Validate VLM JSON"""
        if value is not None and not isinstance(value, (dict, list)):
            raise serializers.ValidationError("VLM JSON must be a valid JSON object or array")
        return value


class QPDataListSerializer(serializers.ModelSerializer):
    """Serializer for listing QP Data with minimal fields"""
    ocr_summary = serializers.SerializerMethodField()
    rubric_summary = serializers.SerializerMethodField()
    reference_summary = serializers.SerializerMethodField()
    vlm_summary = serializers.SerializerMethodField()
    is_complete = serializers.SerializerMethodField()

    class Meta:
        model = QPData
        fields = [
            'id',
            'question_paper_uuid',
            'ocr_summary',
            'rubric_summary',
            'reference_summary',
            'vlm_summary',
            'is_complete',
            'created_at'
        ]

    def get_ocr_summary(self, obj):
        return obj.get_ocr_summary()

    def get_rubric_summary(self, obj):
        return obj.get_rubric_summary()

    def get_reference_summary(self, obj):
        return obj.get_reference_summary()

    def get_vlm_summary(self, obj):
        return obj.get_vlm_summary()

    def get_is_complete(self, obj):
        return obj.is_complete()


class QPDataProcessSerializer(serializers.Serializer):
    """Serializer for processing QP JSON data from ML"""
    question_paper_uuid = serializers.UUIDField()
    ocr_json = serializers.JSONField(required=False, allow_null=True)
    rubric_json = serializers.JSONField(required=False, allow_null=True)
    reference_json = serializers.JSONField(required=False, allow_null=True)
    vlm_json = serializers.JSONField(required=False, allow_null=True)

    def validate(self, data):
        """Ensure at least one JSON field is provided"""
        if not any([data.get('ocr_json'), data.get('rubric_json'), 
                   data.get('reference_json'), data.get('vlm_json')]):
            raise serializers.ValidationError(
                "At least one of 'ocr_json', 'rubric_json', 'reference_json', or 'vlm_json' must be provided"
            )
        return data

    def validate_ocr_json(self, value):
        if value is not None and not isinstance(value, (dict, list)):
            raise serializers.ValidationError("OCR JSON must be a valid JSON object or array")
        return value

    def validate_rubric_json(self, value):
        if value is not None and not isinstance(value, (dict, list)):
            raise serializers.ValidationError("Rubric JSON must be a valid JSON object or array")
        return value

    def validate_reference_json(self, value):
        if value is not None and not isinstance(value, (dict, list)):
            raise serializers.ValidationError("Reference JSON must be a valid JSON object or array")
        return value

    def validate_vlm_json(self, value):
        if value is not None and not isinstance(value, (dict, list)):
            raise serializers.ValidationError("VLM JSON must be a valid JSON object or array")
        return value



class ProcessRubricDataSerializer(serializers.Serializer):
    """
    Serializer for processing rubric data with raw JSON input
    Compatible with the rubric_db_updater.py script format
    """
    question_paper_uuid = serializers.UUIDField(
        help_text="Question Paper UUID"
    )
    input_data = serializers.JSONField(
        help_text="Raw JSON data containing rubric information"
    )
    
    def validate_input_data(self, value):
        """Validate that input_data is valid JSON"""
        if not isinstance(value, (dict, list)):
            raise serializers.ValidationError(
                "input_data must be a valid JSON object or array"
            )
        return value
    
    def process_rubric(self):
        """
        Process the rubric data using RubricProcessor
        Returns: (rubric_data, reference_data)
        """
        validated_data = self.validated_data
        input_data = validated_data['input_data']
        
        try:
            return RubricProcessor.process_rubric_data(input_data)
        except Exception as e:
            raise serializers.ValidationError(f"Failed to process rubric data: {str(e)}")