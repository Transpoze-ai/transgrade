# ============================================================================
# qp_data/views.py
# ============================================================================

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.db import transaction
from .models import QPData
from .serializers import (
    QPDataSerializer,
    QPDataListSerializer,
    QPDataProcessSerializer
)
from .rubric_processor import RubricProcessor
from .serializers import ProcessRubricDataSerializer
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
def process_qp_json(request):
    """
    Process QP JSON data from ML and create/update QP data entry
    Expected JSON format:
    {
        "question_paper_uuid": "123e4567-e89b-12d3-a456-426614174000",
        "ocr_json": {...},          # Optional
        "rubric_json": {...},       # Optional
        "reference_json": {...},    # Optional
        "vlm_json": {...}           # Optional
    }
    """
    try:
        # Validate the input data structure
        process_serializer = QPDataProcessSerializer(data=request.data)
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
        ocr_json = validated_data.get('ocr_json')
        rubric_json = validated_data.get('rubric_json')
        reference_json = validated_data.get('reference_json')
        vlm_json = validated_data.get('vlm_json')

        # Use transaction to ensure consistency
        with transaction.atomic():
            # Check if entry already exists
            qp_data, created = QPData.objects.get_or_create(
                question_paper_uuid=question_paper_uuid,
                defaults={
                    'ocr_json': ocr_json,
                    'rubric_json': rubric_json,
                    'reference_json': reference_json,
                    'vlm_json': vlm_json
                }
            )

            if not created:
                # Update existing entry
                update_fields = []
                if ocr_json is not None:
                    qp_data.ocr_json = ocr_json
                    update_fields.append('ocr_json')
                if rubric_json is not None:
                    qp_data.rubric_json = rubric_json
                    update_fields.append('rubric_json')
                if reference_json is not None:
                    qp_data.reference_json = reference_json
                    update_fields.append('reference_json')
                if vlm_json is not None:
                    qp_data.vlm_json = vlm_json
                    update_fields.append('vlm_json')
                
                if update_fields:
                    update_fields.append('updated_at')
                    qp_data.save(update_fields=update_fields)

        # Serialize the result
        serializer = QPDataSerializer(qp_data)
        
        response_data = {
            'success': True,
            'message': 'Created new QP data entry' if created else 'Updated existing QP data entry',
            'created': created,
            'question_paper_uuid': str(question_paper_uuid),
            'data': serializer.data
        }

        return Response(
            response_data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to process QP JSON: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def create_qp_data(request):
    """Create a new QP data entry"""
    serializer = QPDataSerializer(data=request.data)
    if serializer.is_valid():
        try:
            serializer.save()
            return Response(
                {
                    'success': True,
                    'message': 'QP data created successfully',
                    'data': serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': f'Failed to create QP data: {str(e)}'
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
def get_qp_data_by_id(request, qp_id):
    """Get QP data by ID"""
    try:
        qp_data = get_object_or_404(QPData, id=qp_id)
        serializer = QPDataSerializer(qp_data)
        return Response({
            'success': True,
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to retrieve QP data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_qp_data_by_uuid(request, question_paper_uuid):
    """Get QP data by question paper UUID"""
    try:
        qp_data = get_object_or_404(QPData, question_paper_uuid=question_paper_uuid)
        serializer = QPDataSerializer(qp_data)
        return Response({
            'success': True,
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to retrieve QP data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT'])
def update_qp_data(request, qp_id):
    """Update QP data by ID"""
    try:
        qp_data = get_object_or_404(QPData, id=qp_id)
        serializer = QPDataSerializer(qp_data, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'QP data updated successfully',
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
                'error': f'Failed to update QP data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
def delete_qp_data(request, qp_id):
    """Delete QP data by ID"""
    try:
        qp_data = get_object_or_404(QPData, id=qp_id)
        qp_data.delete()
        return Response(
            {
                'success': True,
                'message': 'QP data deleted successfully'
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to delete QP data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def list_qp_data(request):
    """List all QP data"""
    try:
        qp_data = QPData.objects.all().order_by('-created_at')
        serializer = QPDataListSerializer(qp_data, many=True)
        return Response({
            'success': True,
            'count': len(qp_data),
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to list QP data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def search_qp_data(request):
    """Search QP data by question paper UUID and data availability"""
    try:
        question_paper_uuid = request.GET.get('uuid', '')
        has_ocr = request.GET.get('has_ocr', '').lower()
        has_rubric = request.GET.get('has_rubric', '').lower()
        has_reference = request.GET.get('has_reference', '').lower()
        has_vlm = request.GET.get('has_vlm', '').lower()
        is_complete = request.GET.get('is_complete', '').lower()

        queryset = QPData.objects.all()

        if question_paper_uuid:
            queryset = queryset.filter(question_paper_uuid__icontains=question_paper_uuid)

        if has_ocr in ['true', '1']:
            queryset = queryset.exclude(ocr_json__isnull=True)
        elif has_ocr in ['false', '0']:
            queryset = queryset.filter(ocr_json__isnull=True)

        if has_rubric in ['true', '1']:
            queryset = queryset.exclude(rubric_json__isnull=True)
        elif has_rubric in ['false', '0']:
            queryset = queryset.filter(rubric_json__isnull=True)

        if has_reference in ['true', '1']:
            queryset = queryset.exclude(reference_json__isnull=True)
        elif has_reference in ['false', '0']:
            queryset = queryset.filter(reference_json__isnull=True)

        if has_vlm in ['true', '1']:
            queryset = queryset.exclude(vlm_json__isnull=True)
        elif has_vlm in ['false', '0']:
            queryset = queryset.filter(vlm_json__isnull=True)

        if is_complete in ['true', '1']:
            queryset = queryset.exclude(
                Q(ocr_json__isnull=True) | Q(rubric_json__isnull=True) | 
                Q(reference_json__isnull=True) | Q(vlm_json__isnull=True)
            )
        elif is_complete in ['false', '0']:
            queryset = queryset.filter(
                Q(ocr_json__isnull=True) | Q(rubric_json__isnull=True) | 
                Q(reference_json__isnull=True) | Q(vlm_json__isnull=True)
            )

        queryset = queryset.order_by('-created_at')
        serializer = QPDataListSerializer(queryset, many=True)

        return Response({
            'success': True,
            'count': len(queryset),
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to search QP data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_qp_data_status(request):
    """Get QP data processing status statistics"""
    try:
        total_count = QPData.objects.count()
        has_ocr_count = QPData.objects.exclude(ocr_json__isnull=True).count()
        has_rubric_count = QPData.objects.exclude(rubric_json__isnull=True).count()
        has_reference_count = QPData.objects.exclude(reference_json__isnull=True).count()
        has_vlm_count = QPData.objects.exclude(vlm_json__isnull=True).count()
        complete_count = QPData.objects.exclude(
            Q(ocr_json__isnull=True) | Q(rubric_json__isnull=True) | 
            Q(reference_json__isnull=True) | Q(vlm_json__isnull=True)
        ).count()

        return Response({
            'success': True,
            'statistics': {
                'total_question_papers': total_count,
                'with_ocr_data': has_ocr_count,
                'with_rubric_data': has_rubric_count,
                'with_reference_data': has_reference_count,
                'with_vlm_data': has_vlm_count,
                'complete_processing': complete_count,
                'ocr_completion_rate': (has_ocr_count / total_count * 100) if total_count > 0 else 0,
                'rubric_completion_rate': (has_rubric_count / total_count * 100) if total_count > 0 else 0,
                'reference_completion_rate': (has_reference_count / total_count * 100) if total_count > 0 else 0,
                'vlm_completion_rate': (has_vlm_count / total_count * 100) if total_count > 0 else 0,
                'overall_completion_rate': (complete_count / total_count * 100) if total_count > 0 else 0
            }
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to get QP data status: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )













@api_view(['POST'])
def process_rubric_data(request):
    """
    Process rubric data and update QPData with rubric_json and reference_json
    
    This endpoint is compatible with the rubric_db_updater.py script.
    
    Expected JSON format:
    {
        "question_paper_uuid": "123e4567-e89b-12d3-a456-426614174000",
        "input_data": {
            // Raw rubric JSON structure from ML processing
            "django_response": {
                "data": {
                    "rubric_json": {
                        "individual_pages": [
                            {
                                "rubric_json": [
                                    {
                                        "question": "What is...",
                                        "reference_answer": "The answer is...",
                                        "marks": 10
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
        }
    }
    
    Alternative formats are also supported:
    - Direct individual_pages structure
    - List of page objects
    - Various question/answer key naming conventions
    """
    try:
        # Validate input data
        serializer = ProcessRubricDataSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'errors': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Extract validated data
        question_paper_uuid = serializer.validated_data['question_paper_uuid']
        input_data = serializer.validated_data['input_data']
        
        logger.info(f"Processing rubric data for UUID: {question_paper_uuid}")
        
        # Process rubric data
        try:
            rubric_data, reference_data = serializer.process_rubric()
        except serializers.ValidationError as ve:
            return Response(
                {
                    'success': False,
                    'error': str(ve)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Use database transaction for consistency
        with transaction.atomic():
            # Get or create QPData entry
            qp_data, created = QPData.objects.get_or_create(
                question_paper_uuid=question_paper_uuid,
                defaults={
                    'rubric_json': rubric_data,
                    'reference_json': reference_data
                }
            )
            
            # Update existing entry if it already exists
            if not created:
                update_fields = []
                
                # Update rubric_json if we have data
                if rubric_data:
                    qp_data.rubric_json = rubric_data
                    update_fields.append('rubric_json')
                
                # Update reference_json if we have data
                if reference_data:
                    qp_data.reference_json = reference_data
                    update_fields.append('reference_json')
                
                # Save if there are updates
                if update_fields:
                    update_fields.append('updated_at')
                    qp_data.save(update_fields=update_fields)
        
        # Prepare response
        action = "Created new" if created else "Updated existing"
        serialized_data = QPDataSerializer(qp_data).data
        
        response_data = {
            'success': True,
            'message': f'{action} QP data with rubric processing',
            'created': created,
            'question_paper_uuid': str(question_paper_uuid),
            'processing_summary': {
                'rubric_items_processed': len(rubric_data),
                'reference_qa_pairs_extracted': len(reference_data),
                'has_rubric_data': bool(rubric_data),
                'has_reference_data': bool(reference_data)
            },
            'data': serialized_data
        }
        
        logger.info(f"Successfully processed rubric data: {len(rubric_data)} rubric items, {len(reference_data)} QA pairs")
        
        return Response(
            response_data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Unexpected error processing rubric data: {e}")
        return Response(
            {
                'success': False,
                'error': f'Failed to process rubric data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def process_rubric_separate(request):
    """
    Alternative endpoint that processes rubric data and returns processed data
    without immediately saving to database. Useful for preview/validation.
    
    Same input format as process_rubric_data but returns processed data
    without database operations.
    """
    try:
        # Validate input data
        serializer = ProcessRubricDataSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'errors': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Process rubric data without saving
        question_paper_uuid = serializer.validated_data['question_paper_uuid']
        
        try:
            rubric_data, reference_data = serializer.process_rubric()
        except serializers.ValidationError as ve:
            return Response(
                {
                    'success': False,
                    'error': str(ve)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        response_data = {
            'success': True,
            'message': 'Rubric data processed successfully (not saved)',
            'question_paper_uuid': str(question_paper_uuid),
            'processing_summary': {
                'rubric_items_processed': len(rubric_data),
                'reference_qa_pairs_extracted': len(reference_data),
                'has_rubric_data': bool(rubric_data),
                'has_reference_data': bool(reference_data)
            },
            'processed_data': {
                'rubric_json': rubric_data,
                'reference_json': reference_data
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in process_rubric_separate: {e}")
        return Response(
            {
                'success': False,
                'error': f'Failed to process rubric data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
