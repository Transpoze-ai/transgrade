# serializers.py for chunk_data app
from rest_framework import serializers
from .models import ChunkData


class ChunkDataSerializer(serializers.ModelSerializer):
    total_chunks = serializers.SerializerMethodField(read_only=True)
    total_pages = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ChunkData
        fields = [
            'id',
            'question_paper_uuid',
            'roll_no',
            'chunk_data',
            'total_chunks',
            'total_pages',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_total_chunks(self, obj):
        return obj.get_total_chunks()

    def get_total_pages(self, obj):
        return obj.get_total_pages()

    def validate(self, data):
        """
        Check that roll_no and question_paper_uuid combination is unique for new instances
        """
        if self.instance is None:  # Creating new instance
            roll_no = data.get('roll_no')
            question_paper_uuid = data.get('question_paper_uuid')

            if ChunkData.objects.filter(
                roll_no=roll_no,
                question_paper_uuid=question_paper_uuid
            ).exists():
                raise serializers.ValidationError(
                    "Chunk data for this roll number and question paper UUID already exists"
                )
        return data

    def validate_chunk_data(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Chunk data must be a valid JSON object")
        
        # Validate required fields in chunk_data
        required_fields = ['chunks', 'total_chunks', 'total_pages']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Chunk data must contain '{field}' field")
        
        # Validate chunks structure
        chunks = value.get('chunks', [])
        if not isinstance(chunks, list):
            raise serializers.ValidationError("'chunks' must be a list")
        
        for chunk in chunks:
            if not isinstance(chunk, dict):
                raise serializers.ValidationError("Each chunk must be a dictionary")
            if 'chunk_id' not in chunk or 'chunk_text' not in chunk:
                raise serializers.ValidationError("Each chunk must have 'chunk_id' and 'chunk_text'")
        
        return value


class ChunkDataListSerializer(serializers.ModelSerializer):
    total_chunks = serializers.SerializerMethodField()
    total_pages = serializers.SerializerMethodField()

    class Meta:
        model = ChunkData
        fields = [
            'id',
            'question_paper_uuid',
            'roll_no',
            'total_chunks',
            'total_pages',
            'created_at'
        ]

    def get_total_chunks(self, obj):
        return obj.get_total_chunks()

    def get_total_pages(self, obj):
        return obj.get_total_pages()


class ChunkDataProcessSerializer(serializers.Serializer):
    """Serializer for processing chunk JSON data"""
    question_paper_uuid = serializers.UUIDField()
    roll_no = serializers.CharField(max_length=50)
    chunks = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False
    )
    page_info = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True,
        required=False
    )
    total_chunks = serializers.IntegerField(min_value=0)
    total_pages = serializers.IntegerField(min_value=0)
    success = serializers.BooleanField(required=False, default=True)

    def validate_chunks(self, value):
        """Validate chunks structure"""
        for chunk in value:
            if not isinstance(chunk, dict):
                raise serializers.ValidationError("Each chunk must be a dictionary")
            
            if 'chunk_id' not in chunk:
                raise serializers.ValidationError("Each chunk must have 'chunk_id'")
            
            if 'chunk_text' not in chunk:
                raise serializers.ValidationError("Each chunk must have 'chunk_text'")
                
        return value