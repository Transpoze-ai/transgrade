from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.db import transaction
from .models import OCRData
from .serializers import (
    OCRDataSerializer,
    OCRDataListSerializer,
    OCRDataByUUIDSerializer,
    OCRDataProcessSerializer
)


@api_view(['POST'])
def process_ocr_json(request):
    """
    Process OCR JSON data and create multiple OCR data entries
    Expected JSON format:
    {
        "question_paper_uuid": "123e4567-e89b-12d3-a456-426614174000",
        "roll_no": "5",
        "ocr_results": [
            {
                "image_index": 0,
                "ocr_result": {...}
            },
            ...
        ]
    }
    """
    try:
        # Validate the input data structure
        process_serializer = OCRDataProcessSerializer(data=request.data)
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
        ocr_results = validated_data['ocr_results']

        created_entries = []
        updated_entries = []
        errors = []

        # Use transaction to ensure all operations succeed or fail together
        with transaction.atomic():
            for ocr_item in ocr_results:
                image_index = ocr_item['image_index']
                ocr_result = ocr_item['ocr_result']

                # Prepare data for OCRData model
                ocr_data_dict = {
                    'question_paper_uuid': question_paper_uuid,
                    'roll_no': roll_no,
                    'page_number': image_index,  # image_index becomes page_number
                    'ocr_json_dump': ocr_result  # ocr_result becomes ocr_json_dump
                }

                try:
                    # Check if entry already exists
                    existing_entry = OCRData.objects.filter(
                        question_paper_uuid=question_paper_uuid,
                        roll_no=roll_no,
                        page_number=image_index
                    ).first()

                    if existing_entry:
                        # Update existing entry
                        serializer = OCRDataSerializer(existing_entry, data=ocr_data_dict, partial=True)
                        if serializer.is_valid():
                            serializer.save()
                            updated_entries.append(serializer.data)
                        else:
                            errors.append({
                                'page_number': image_index,
                                'errors': serializer.errors
                            })
                    else:
                        # Create new entry
                        serializer = OCRDataSerializer(data=ocr_data_dict)
                        if serializer.is_valid():
                            serializer.save()
                            created_entries.append(serializer.data)
                        else:
                            errors.append({
                                'page_number': image_index,
                                'errors': serializer.errors
                            })

                except Exception as e:
                    errors.append({
                        'page_number': image_index,
                        'error': f'Processing error: {str(e)}'
                    })

        # Prepare response
        response_data = {
            'success': len(errors) == 0,
            'question_paper_uuid': str(question_paper_uuid),
            'roll_no': roll_no,
            'total_processed': len(ocr_results),
            'created_count': len(created_entries),
            'updated_count': len(updated_entries),
            'error_count': len(errors),
            'created_entries': created_entries,
            'updated_entries': updated_entries
        }

        if errors:
            response_data['errors'] = errors

        return Response(
            response_data,
            status=status.HTTP_200_OK if len(errors) == 0 else status.HTTP_207_MULTI_STATUS
        )

    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to process OCR JSON: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def create_ocr_data(request):
    """Create a new OCR data entry"""
    serializer = OCRDataSerializer(data=request.data)
    if serializer.is_valid():
        try:
            serializer.save()
            return Response(
                {
                    'success': True,
                    'message': 'OCR data created successfully',
                    'data': serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': f'Failed to create OCR data: {str(e)}'
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
def get_ocr_data_by_id(request, ocr_id):
    """Get OCR data by ID"""
    try:
        ocr_data = get_object_or_404(OCRData, id=ocr_id)
        serializer = OCRDataSerializer(ocr_data)
        return Response({
            'success': True,
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to retrieve OCR data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_ocr_data_by_roll_and_uuid(request, roll_no, question_paper_uuid):
    """Get all OCR data for a specific roll number and question paper UUID"""
    try:
        ocr_data = OCRData.objects.filter(
            roll_no=roll_no,
            question_paper_uuid=question_paper_uuid
        ).order_by('page_number')
        serializer = OCRDataSerializer(ocr_data, many=True)
        return Response({
            'success': True,
            'roll_no': roll_no,
            'question_paper_uuid': str(question_paper_uuid),
            'count': len(ocr_data),
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to retrieve OCR data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_ocr_data_by_roll_uuid_page(request, roll_no, question_paper_uuid, page_number):
    """Get specific OCR data by roll number, question paper UUID, and page number"""
    try:
        ocr_data = get_object_or_404(
            OCRData,
            roll_no=roll_no,
            question_paper_uuid=question_paper_uuid,
            page_number=page_number
        )
        serializer = OCRDataSerializer(ocr_data)
        return Response({
            'success': True,
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to retrieve OCR data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT'])
def update_ocr_data(request, ocr_id):
    """Update OCR data by ID"""
    try:
        ocr_data = get_object_or_404(OCRData, id=ocr_id)
        serializer = OCRDataSerializer(ocr_data, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'OCR data updated successfully',
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
                'error': f'Failed to update OCR data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
def delete_ocr_data(request, ocr_id):
    """Delete OCR data by ID"""
    try:
        ocr_data = get_object_or_404(OCRData, id=ocr_id)
        ocr_data.delete()
        return Response(
            {
                'success': True,
                'message': 'OCR data deleted successfully'
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to delete OCR data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def list_ocr_data(request):
    """List all OCR data"""
    try:
        ocr_data = OCRData.objects.all().order_by('question_paper_uuid', 'roll_no', 'page_number')
        serializer = OCRDataListSerializer(ocr_data, many=True)
        return Response({
            'success': True,
            'count': len(ocr_data),
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to list OCR data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def filter_by_question_paper(request, question_paper_uuid):
    """Get all OCR data for a specific question paper UUID"""
    try:
        ocr_data = OCRData.objects.filter(
            question_paper_uuid=question_paper_uuid
        ).order_by('roll_no', 'page_number')
        serializer = OCRDataByUUIDSerializer(ocr_data, many=True)
        return Response({
            'success': True,
            'question_paper_uuid': str(question_paper_uuid),
            'count': len(ocr_data),
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to filter OCR data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def search_ocr_data(request):
    """Search OCR data by roll number, question paper UUID, or text content"""
    try:
        roll_no = request.GET.get('roll_no', '')
        question_paper_uuid = request.GET.get('question_paper_uuid', '')
        text_search = request.GET.get('text', '')

        queryset = OCRData.objects.all()

        if roll_no:
            queryset = queryset.filter(roll_no__icontains=roll_no)

        if question_paper_uuid:
            queryset = queryset.filter(question_paper_uuid=question_paper_uuid)

        if text_search:
            # Search in OCR JSON dump - this is a basic search, you might want to improve it
            queryset = queryset.filter(
                Q(ocr_json_dump__icontains=text_search)
            )

        queryset = queryset.order_by('question_paper_uuid', 'roll_no', 'page_number')
        serializer = OCRDataListSerializer(queryset, many=True)

        return Response({
            'success': True,
            'count': len(queryset),
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to search OCR data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def bulk_create_ocr_data(request):
    """Create multiple OCR data entries at once"""
    try:
        if not isinstance(request.data, list):
            return Response(
                {
                    'success': False,
                    'error': 'Request data must be a list of OCR data objects'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = OCRDataSerializer(data=request.data, many=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    'success': True,
                    'message': f'{len(request.data)} OCR data entries created successfully',
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
                'error': f'Failed to create OCR data: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )