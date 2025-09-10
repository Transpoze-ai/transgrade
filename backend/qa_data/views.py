from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.db import transaction
from .models import QAData
from .serializers import (
    QADataSerializer,
    QADataListSerializer,
    QADataByUUIDSerializer,
    QADataProcessSerializer,
    VLMDataSerializer
)
from .utils import parse_processing_timestamp


@api_view(['POST'])
def process_qa_json(request):
    """
    Process QA JSON data and create/update QA data entry
    Now supports VLM data as well
    Expected JSON format:
    {
        "data": {
            "processing_timestamp": "2025-08-22T11:54:12.729553",
            "qa_mapping": [...],
            "vlm_json": {...} (optional),
            "vlm_restructured_json": {...} (optional),
            "question_paper_uuid": "123e4567-e89b-12d3-a456-426614174000",
            "roll_no": "5",
            "total_questions_processed": 8
        },
        "success": true
    }
    """
    try:
        # Validate the input data structure
        process_serializer = QADataProcessSerializer(data=request.data)
        if not process_serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'errors': process_serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        validated_data = process_serializer.validated_data
        data_payload = validated_data['data']
        
        question_paper_uuid = data_payload['question_paper_uuid']
        roll_no = str(data_payload['roll_no'])
        qa_mapping = data_payload['qa_mapping']
        vlm_json = data_payload.get('vlm_json')
        vlm_restructured_json = data_payload.get('vlm_restructured_json')
        total_questions_processed = data_payload.get('total_questions_processed', len(qa_mapping))
        processing_timestamp_str = data_payload.get('processing_timestamp')

        # Parse processing timestamp
        processing_timestamp = None
        if processing_timestamp_str:
            processing_timestamp = parse_processing_timestamp(processing_timestamp_str)

        # Prepare data for QAData model
        qa_data_dict = {
            'question_paper_uuid': question_paper_uuid,
            'roll_no': roll_no,
            'qa_mapping': qa_mapping,
            'vlm_json': vlm_json,
            'vlm_restructured_json': vlm_restructured_json,
            'total_questions_processed': total_questions_processed,
            'processing_timestamp': processing_timestamp
        }

        # Use transaction to ensure atomicity
        with transaction.atomic():
            # Check if entry already exists
            existing_entry = QAData.objects.filter(
                question_paper_uuid=question_paper_uuid,
                roll_no=roll_no
            ).first()

            if existing_entry:
                # Update existing entry
                serializer = QADataSerializer(existing_entry, data=qa_data_dict, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response({
                        'success': True,
                        'message': 'QA data updated successfully',
                        'action': 'updated',
                        'question_paper_uuid': str(question_paper_uuid),
                        'roll_no': roll_no,
                        'data': serializer.data
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'success': False,
                        'errors': serializer.errors
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                # Create new entry
                serializer = QADataSerializer(data=qa_data_dict)
                if serializer.is_valid():
                    serializer.save()
                    return Response({
                        'success': True,
                        'message': 'QA data created successfully',
                        'action': 'created',
                        'question_paper_uuid': str(question_paper_uuid),
                        'roll_no': roll_no,
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
                'error': f'Failed to process QA JSON: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def create_qa_data(request):
    """Create a new QA data entry"""
    serializer = QADataSerializer(data=request.data)
    if serializer.is_valid():
        try:
            serializer.save()
            return Response(
                {
                    'success': True,
                    'message': 'QA data created successfully',
                    'data': serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': f'Failed to create QA data: {str(e)}'
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
def get_qa_data_by_id(request, qa_id):
    """Get QA data by ID"""
    try:
        qa_data = get_object_or_404(QAData, id=qa_id)
        serializer = QADataSerializer(qa_data)
        return Response({
            'success': True,
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to retrieve QA data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_qa_data_by_roll_and_uuid(request, roll_no, question_paper_uuid):
    """Get QA data for a specific roll number and question paper UUID"""
    try:
        qa_data = get_object_or_404(
            QAData,
            roll_no=roll_no,
            question_paper_uuid=question_paper_uuid
        )
        serializer = QADataSerializer(qa_data)
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
                'error': f'Failed to retrieve QA data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT'])
def update_qa_data(request, qa_id):
    """Update QA data by ID"""
    try:
        qa_data = get_object_or_404(QAData, id=qa_id)
        serializer = QADataSerializer(qa_data, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'QA data updated successfully',
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
                'error': f'Failed to update QA data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
def delete_qa_data(request, qa_id):
    """Delete QA data by ID"""
    try:
        qa_data = get_object_or_404(QAData, id=qa_id)
        qa_data.delete()
        return Response(
            {
                'success': True,
                'message': 'QA data deleted successfully'
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to delete QA data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def list_qa_data(request):
    """List all QA data"""
    try:
        qa_data = QAData.objects.all().order_by('question_paper_uuid', 'roll_no')
        serializer = QADataListSerializer(qa_data, many=True)
        return Response({
            'success': True,
            'count': len(qa_data),
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to list QA data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def filter_by_question_paper(request, question_paper_uuid):
    """Get all QA data for a specific question paper UUID"""
    try:
        qa_data = QAData.objects.filter(
            question_paper_uuid=question_paper_uuid
        ).order_by('roll_no')
        serializer = QADataByUUIDSerializer(qa_data, many=True)
        return Response({
            'success': True,
            'question_paper_uuid': str(question_paper_uuid),
            'count': len(qa_data),
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to filter QA data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def search_qa_data(request):
    """Search QA data by roll number, question paper UUID, or QA content"""
    try:
        roll_no = request.GET.get('roll_no', '')
        question_paper_uuid = request.GET.get('question_paper_uuid', '')
        text_search = request.GET.get('text', '')

        queryset = QAData.objects.all()

        if roll_no:
            queryset = queryset.filter(roll_no__icontains=roll_no)

        if question_paper_uuid:
            queryset = queryset.filter(question_paper_uuid=question_paper_uuid)

        if text_search:
            # Search in QA mapping - this is a basic search, you might want to improve it
            queryset = queryset.filter(
                Q(qa_mapping__icontains=text_search)
            )

        queryset = queryset.order_by('question_paper_uuid', 'roll_no')
        serializer = QADataListSerializer(queryset, many=True)

        return Response({
            'success': True,
            'count': len(queryset),
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to search QA data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def bulk_create_qa_data(request):
    """Create multiple QA data entries at once"""
    try:
        if not isinstance(request.data, list):
            return Response(
                {
                    'success': False,
                    'error': 'Request data must be a list of QA data objects'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = QADataSerializer(data=request.data, many=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    'success': True,
                    'message': f'{len(request.data)} QA data entries created successfully',
                    'data': serializer.data
                },
                status=status.HTTP_201_CREATED
            )
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
                'error': f'Failed to create QA data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



@api_view(['GET'])
def get_vlm_data(request, qa_id):
    """Get VLM data by QA ID"""
    try:
        qa_data = get_object_or_404(QAData, id=qa_id)
        serializer = VLMDataSerializer(qa_data)
        return Response({
            'success': True,
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to retrieve VLM data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT', 'PATCH'])
def update_vlm_data(request, qa_id):
    """Update VLM data by QA ID"""
    try:
        qa_data = get_object_or_404(QAData, id=qa_id)
        serializer = VLMDataSerializer(qa_data, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'VLM data updated successfully',
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
                'error': f'Failed to update VLM data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
def delete_vlm_data(request, qa_id):
    """Delete VLM data (set to null) by QA ID"""
    try:
        qa_data = get_object_or_404(QAData, id=qa_id)
        qa_data.vlm_json = None
        qa_data.vlm_restructured_json = None
        qa_data.save()
        return Response({
            'success': True,
            'message': 'VLM data deleted successfully'
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to delete VLM data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_vlm_data_by_roll_and_uuid(request, roll_no, question_paper_uuid):
    """Get VLM data by roll number and question paper UUID"""
    try:
        qa_data = get_object_or_404(
            QAData,
            roll_no=roll_no,
            question_paper_uuid=question_paper_uuid
        )
        serializer = VLMDataSerializer(qa_data)
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
                'error': f'Failed to retrieve VLM data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT', 'PATCH'])
def update_vlm_data_by_roll_and_uuid(request, roll_no, question_paper_uuid):
    """Update VLM data by roll number and question paper UUID"""
    try:
        qa_data = get_object_or_404(
            QAData,
            roll_no=roll_no,
            question_paper_uuid=question_paper_uuid
        )
        serializer = VLMDataSerializer(qa_data, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'VLM data updated successfully',
                'roll_no': roll_no,
                'question_paper_uuid': str(question_paper_uuid),
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
                'error': f'Failed to update VLM data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
