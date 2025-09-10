# views.py for chunk_data app
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.db import transaction
from .models import ChunkData
from .serializers import (
    ChunkDataSerializer,
    ChunkDataListSerializer,
    ChunkDataProcessSerializer
)


@api_view(['POST'])
def process_chunk_json(request):
    """
    Process chunk JSON data and create/update chunk data entry
    Expected JSON format:
    {
        "chunks": [...],
        "page_info": [...],
        "question_paper_uuid": "123e4567-e89b-12d3-a456-426614174000",
        "roll_no": "5",
        "success": true,
        "total_chunks": 21,
        "total_pages": 4
    }
    """
    try:
        # Validate the input data structure
        process_serializer = ChunkDataProcessSerializer(data=request.data)
        if not process_serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'errors': process_serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        validated_data = process_serializer.validated_data
        question_paper_uuid = validated_data['question_paper_uuid']
        roll_no = validated_data['roll_no']

        # Prepare the complete chunk data
        chunk_data_dict = {
            'question_paper_uuid': question_paper_uuid,
            'roll_no': roll_no,
            'chunk_data': {
                'chunks': validated_data['chunks'],
                'page_info': validated_data.get('page_info', []),
                'question_paper_uuid': str(question_paper_uuid),
                'roll_no': roll_no,
                'success': validated_data.get('success', True),
                'total_chunks': validated_data['total_chunks'],
                'total_pages': validated_data['total_pages']
            }
        }

        # Use transaction to ensure operation succeeds or fails completely
        with transaction.atomic():
            # Check if entry already exists
            existing_entry = ChunkData.objects.filter(
                question_paper_uuid=question_paper_uuid,
                roll_no=roll_no
            ).first()

            if existing_entry:
                # Update existing entry
                serializer = ChunkDataSerializer(existing_entry, data=chunk_data_dict, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response({
                        'success': True,
                        'message': 'Chunk data updated successfully',
                        'action': 'updated',
                        'data': serializer.data
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'success': False,
                        'errors': serializer.errors
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                # Create new entry
                serializer = ChunkDataSerializer(data=chunk_data_dict)
                if serializer.is_valid():
                    serializer.save()
                    return Response({
                        'success': True,
                        'message': 'Chunk data created successfully',
                        'action': 'created',
                        'data': serializer.data
                    }, status=status.HTTP_201_CREATED)
                else:
                    return Response({
                        'success': False,
                        'errors': serializer.errors
                    }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to process chunk JSON: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def create_chunk_data(request):
    """Create a new chunk data entry"""
    serializer = ChunkDataSerializer(data=request.data)
    if serializer.is_valid():
        try:
            serializer.save()
            return Response(
                {
                    'success': True,
                    'message': 'Chunk data created successfully',
                    'data': serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': f'Failed to create chunk data: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    return Response(
        {
            'success': False,
            'errors': serializer.errors
        },
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
def get_chunk_data_by_id(request, chunk_id):
    """Get chunk data by ID"""
    try:
        chunk_data = get_object_or_404(ChunkData, id=chunk_id)
        serializer = ChunkDataSerializer(chunk_data)
        return Response({
            'success': True,
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to retrieve chunk data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_chunk_data_by_roll_and_uuid(request, roll_no, question_paper_uuid):
    """Get chunk data for a specific roll number and question paper UUID"""
    try:
        chunk_data = get_object_or_404(
            ChunkData,
            roll_no=roll_no,
            question_paper_uuid=question_paper_uuid
        )
        serializer = ChunkDataSerializer(chunk_data)
        return Response({
            'success': True,
            'roll_no': roll_no,
            'question_paper_uuid': str(question_paper_uuid),
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to retrieve chunk data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT'])
def update_chunk_data(request, chunk_id):
    """Update chunk data by ID"""
    try:
        chunk_data = get_object_or_404(ChunkData, id=chunk_id)
        serializer = ChunkDataSerializer(chunk_data, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Chunk data updated successfully',
                'data': serializer.data
            })
        return Response(
            {
                'success': False,
                'errors': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to update chunk data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
def delete_chunk_data(request, chunk_id):
    """Delete chunk data by ID"""
    try:
        chunk_data = get_object_or_404(ChunkData, id=chunk_id)
        chunk_data.delete()
        return Response(
            {
                'success': True,
                'message': 'Chunk data deleted successfully'
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to delete chunk data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def list_chunk_data(request):
    """List all chunk data"""
    try:
        chunk_data = ChunkData.objects.all().order_by('question_paper_uuid', 'roll_no')
        serializer = ChunkDataListSerializer(chunk_data, many=True)
        return Response({
            'success': True,
            'count': len(chunk_data),
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to list chunk data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def filter_by_question_paper(request, question_paper_uuid):
    """Get all chunk data for a specific question paper UUID"""
    try:
        chunk_data = ChunkData.objects.filter(
            question_paper_uuid=question_paper_uuid
        ).order_by('roll_no')
        serializer = ChunkDataListSerializer(chunk_data, many=True)
        return Response({
            'success': True,
            'question_paper_uuid': str(question_paper_uuid),
            'count': len(chunk_data),
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to filter chunk data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def search_chunk_data(request):
    """Search chunk data by roll number, question paper UUID, or chunk text content"""
    try:
        roll_no = request.GET.get('roll_no', '')
        question_paper_uuid = request.GET.get('question_paper_uuid', '')
        text_search = request.GET.get('text', '')

        queryset = ChunkData.objects.all()

        if roll_no:
            queryset = queryset.filter(roll_no__icontains=roll_no)

        if question_paper_uuid:
            queryset = queryset.filter(question_paper_uuid=question_paper_uuid)

        if text_search:
            # Search in chunk data JSON - searching in chunks text
            queryset = queryset.filter(
                Q(chunk_data__icontains=text_search)
            )

        queryset = queryset.order_by('question_paper_uuid', 'roll_no')
        serializer = ChunkDataListSerializer(queryset, many=True)

        return Response({
            'success': True,
            'count': len(queryset),
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to search chunk data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )