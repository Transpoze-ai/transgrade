from rest_framework import serializers
from .models import AnswerScript
from .utils import process_and_upload_images, validate_image_file, delete_s3_folder


class AnswerScriptSerializer(serializers.ModelSerializer):
    image_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
        help_text="List of image files to upload"
    )
    image_count = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = AnswerScript
        fields = [
            'id',
            'question_paper_uuid',
            'roll_no', 
            'image_urls',
            'image_files',
            'image_count',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_image_count(self, obj):
        return obj.get_image_count()
    
    def validate(self, data):
        """
        Check that roll_no and question_paper_uuid combination is unique for new instances
        """
        if self.instance is None:  # Creating new instance
            roll_no = data.get('roll_no')
            question_paper_uuid = data.get('question_paper_uuid')
            
            if AnswerScript.objects.filter(
                roll_no=roll_no, 
                question_paper_uuid=question_paper_uuid
            ).exists():
                raise serializers.ValidationError(
                    "Answer script with this roll number and question paper UUID already exists"
                )
        return data
    
    def validate_image_files(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("image_files must be a list")
        
        if len(value) == 0:
            raise serializers.ValidationError("At least one image is required")
        
        if len(value) > 50:
            raise serializers.ValidationError("Maximum 50 images allowed")
        
        for i, image_file in enumerate(value):
            is_valid, error = validate_image_file(image_file)
            if not is_valid:
                raise serializers.ValidationError(f"Invalid image at index {i}: {error}")
        
        return value
    
    def create(self, validated_data):
        image_files = validated_data.pop('image_files', [])
        roll_no = validated_data['roll_no']
        question_paper_uuid = validated_data['question_paper_uuid']
        
        if image_files:
            image_urls = process_and_upload_images(roll_no, question_paper_uuid, image_files)
            validated_data['image_urls'] = image_urls
        
        return AnswerScript.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        image_files = validated_data.pop('image_files', None)
        
        if image_files:
            # Delete old images
            old_folder_path = instance.get_s3_folder_path()
            delete_s3_folder(old_folder_path)
            
            # Upload new images
            new_image_urls = process_and_upload_images(
                instance.roll_no, 
                validated_data.get('question_paper_uuid', instance.question_paper_uuid),
                image_files
            )
            validated_data['image_urls'] = new_image_urls
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        return instance


class AnswerScriptListSerializer(serializers.ModelSerializer):
    image_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AnswerScript
        fields = [
            'id', 
            'question_paper_uuid',
            'roll_no', 
            'image_count',
            'created_at'
        ]
    
    def get_image_count(self, obj):
        return obj.get_image_count()


class AnswerScriptByUUIDSerializer(serializers.ModelSerializer):
    image_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AnswerScript
        fields = [
            'id',
            'roll_no',
            'image_count',
            'created_at'
        ]
    
    def get_image_count(self, obj):
        return obj.get_image_count()






# Add this serializer to your serializers.py file

class ProcessExtractionSerializer(serializers.Serializer):
    """Serializer for processing extraction results JSON"""
    question_paper_uuid = serializers.UUIDField(required=True)
    student_groups = serializers.ListField(required=True)
    s3_info = serializers.DictField(required=True)
    
    def validate_student_groups(self, value):
        """Validate student_groups structure"""
        if not isinstance(value, list) or len(value) == 0:
            raise serializers.ValidationError("student_groups must be a non-empty list")
        
        for i, group in enumerate(value):
            if not isinstance(group, dict):
                raise serializers.ValidationError(f"student_groups[{i}] must be a dictionary")
            
            required_fields = ['roll_number', 'page_names']
            for field in required_fields:
                if field not in group:
                    raise serializers.ValidationError(f"student_groups[{i}] missing required field: {field}")
        
        return value
    
    def validate_s3_info(self, value):
        """Validate s3_info structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("s3_info must be a dictionary")
        
        required_fields = ['bucket', 'job_folder']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"s3_info missing required field: {field}")
        
        return value