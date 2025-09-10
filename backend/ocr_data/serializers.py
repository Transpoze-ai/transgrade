from rest_framework import serializers
from .models import OCRData


class OCRDataSerializer(serializers.ModelSerializer):
    text_content = serializers.SerializerMethodField(read_only=True)
    confidence_score = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = OCRData
        fields = [
            'id',
            'question_paper_uuid',
            'roll_no',
            'page_number',
            'ocr_json_dump',
            'text_content',
            'confidence_score',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_text_content(self, obj):
        return obj.get_text_content()

    def get_confidence_score(self, obj):
        return obj.get_confidence_score()

    def validate(self, data):
        """
        Check that roll_no, question_paper_uuid, and page_number combination is unique for new instances
        """
        if self.instance is None:  # Creating new instance
            roll_no = data.get('roll_no')
            question_paper_uuid = data.get('question_paper_uuid')
            page_number = data.get('page_number')

            if OCRData.objects.filter(
                roll_no=roll_no,
                question_paper_uuid=question_paper_uuid,
                page_number=page_number
            ).exists():
                raise serializers.ValidationError(
                    "OCR data for this roll number, question paper UUID, and page number already exists"
                )
        return data

    def validate_page_number(self, value):
        if value < 0:  # Changed to allow 0-based indexing
            raise serializers.ValidationError("Page number must be greater than or equal to 0")
        if value > 100:  # Reasonable limit
            raise serializers.ValidationError("Page number cannot exceed 100")
        return value

    def validate_ocr_json_dump(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("OCR JSON dump must be a valid JSON object")
        return value


class OCRDataListSerializer(serializers.ModelSerializer):
    text_preview = serializers.SerializerMethodField()
    confidence_score = serializers.SerializerMethodField()

    class Meta:
        model = OCRData
        fields = [
            'id',
            'question_paper_uuid',
            'roll_no',
            'page_number',
            'text_preview',
            'confidence_score',
            'created_at'
        ]

    def get_text_preview(self, obj):
        text = obj.get_text_content()
        return text[:100] + "..." if len(text) > 100 else text

    def get_confidence_score(self, obj):
        return obj.get_confidence_score()


class OCRDataByUUIDSerializer(serializers.ModelSerializer):
    text_preview = serializers.SerializerMethodField()
    confidence_score = serializers.SerializerMethodField()

    class Meta:
        model = OCRData
        fields = [
            'id',
            'roll_no',
            'page_number',
            'text_preview',
            'confidence_score',
            'created_at'
        ]

    def get_text_preview(self, obj):
        text = obj.get_text_content()
        return text[:100] + "..." if len(text) > 100 else text

    def get_confidence_score(self, obj):
        return obj.get_confidence_score()


class OCRDataProcessSerializer(serializers.Serializer):
    """Serializer for processing OCR JSON data"""
    question_paper_uuid = serializers.UUIDField()
    roll_no = serializers.CharField(max_length=50)
    ocr_results = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False
    )

    def validate_ocr_results(self, value):
        """Validate ocr_results structure"""
        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError("Each OCR result must be a dictionary")
            
            if 'image_index' not in item:
                raise serializers.ValidationError("Each OCR result must have 'image_index'")
            
            if 'ocr_result' not in item:
                raise serializers.ValidationError("Each OCR result must have 'ocr_result'")
                
            if not isinstance(item['image_index'], int):
                raise serializers.ValidationError("'image_index' must be an integer")
                
        return value