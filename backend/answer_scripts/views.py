from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import AnswerScript
from .serializers import (
    AnswerScriptSerializer, 
    AnswerScriptListSerializer,
    AnswerScriptByUUIDSerializer
)
from .utils import delete_s3_folder


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def create_answer_script(request):
    """Create a new answer script with images"""
    serializer = AnswerScriptSerializer(data=request.data)
    if serializer.is_valid():
        try:
            serializer.save()
            return Response(
                {
                    'success': True,
                    'message': 'Answer script created successfully',
                    'data': serializer.data
                }, 
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': f'Failed to create answer script: {str(e)}'
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
def get_answer_script_by_id(request, script_id):
    """Get answer script by ID"""
    try:
        answer_script = get_object_or_404(AnswerScript, id=script_id)
        serializer = AnswerScriptSerializer(answer_script)
        return Response({
            'success': True,
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to retrieve answer script: {str(e)}'
            }, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_answer_script_by_roll_and_uuid(request, roll_no, question_paper_uuid):
    """Get answer script by roll number and question paper UUID"""
    try:
        answer_script = get_object_or_404(
            AnswerScript, 
            roll_no=roll_no, 
            question_paper_uuid=question_paper_uuid
        )
        serializer = AnswerScriptSerializer(answer_script)
        return Response({
            'success': True,
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to retrieve answer script: {str(e)}'
            }, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def update_answer_script(request, script_id):
    """Update answer script by ID"""
    try:
        answer_script = get_object_or_404(AnswerScript, id=script_id)
        serializer = AnswerScriptSerializer(answer_script, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Answer script updated successfully',
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
                'error': f'Failed to update answer script: {str(e)}'
            }, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
def delete_answer_script(request, script_id):
    """Delete answer script by ID"""
    try:
        answer_script = get_object_or_404(AnswerScript, id=script_id)
        
        # Delete S3 folder
        folder_path = answer_script.get_s3_folder_path()
        delete_s3_folder(folder_path)
        
        answer_script.delete()
        
        return Response(
            {
                'success': True,
                'message': 'Answer script deleted successfully'
            }, 
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to delete answer script: {str(e)}'
            }, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def list_answer_scripts(request):
    """List all answer scripts"""
    try:
        answer_scripts = AnswerScript.objects.all().order_by('question_paper_uuid', 'roll_no')
        serializer = AnswerScriptListSerializer(answer_scripts, many=True)
        return Response({
            'success': True,
            'count': len(answer_scripts),
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to list answer scripts: {str(e)}'
            }, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def filter_by_question_paper(request, question_paper_uuid):
    """Get all answer scripts for a specific question paper UUID"""
    try:
        answer_scripts = AnswerScript.objects.filter(
            question_paper_uuid=question_paper_uuid
        ).order_by('roll_no')
        serializer = AnswerScriptByUUIDSerializer(answer_scripts, many=True)
        return Response({
            'success': True,
            'question_paper_uuid': str(question_paper_uuid),
            'count': len(answer_scripts),
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to filter answer scripts: {str(e)}'
            }, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def get_image_urls_by_roll_and_uuid(request, roll_no, question_paper_uuid):
    """Get image URLs for a specific roll number and question paper UUID"""
    try:
        answer_script = get_object_or_404(
            AnswerScript, 
            roll_no=roll_no,
            question_paper_uuid=question_paper_uuid
        )
        return Response({
            'success': True,
            'roll_no': roll_no,
            'question_paper_uuid': str(answer_script.question_paper_uuid),
            'image_count': answer_script.get_image_count(),
            'image_urls': answer_script.image_urls
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to get image URLs: {str(e)}'
            }, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def search_answer_scripts(request):
    """Search answer scripts by roll number or question paper UUID"""
    try:
        roll_no = request.GET.get('roll_no', '')
        question_paper_uuid = request.GET.get('question_paper_uuid', '')
        
        queryset = AnswerScript.objects.all()
        
        if roll_no:
            queryset = queryset.filter(roll_no__icontains=roll_no)
        
        if question_paper_uuid:
            queryset = queryset.filter(question_paper_uuid=question_paper_uuid)
        
        queryset = queryset.order_by('question_paper_uuid', 'roll_no')
        serializer = AnswerScriptListSerializer(queryset, many=True)
        
        return Response({
            'success': True,
            'count': len(queryset),
            'data': serializer.data
        })
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to search answer scripts: {str(e)}'
            }, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )





# Add this to your views.py file

@api_view(['POST'])
def process_extraction_results(request):
    """Process JSON extraction results and create answer scripts for each student"""
    try:
        # Get JSON data from request
        json_data = request.data
        
        # Validate required fields in JSON
        if 'student_groups' not in json_data or 's3_info' not in json_data:
            return Response(
                {
                    'success': False,
                    'error': 'Invalid JSON format: missing student_groups or s3_info'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Extract question paper UUID from request (you can modify this based on how you want to pass it)
        question_paper_uuid = request.data.get('question_paper_uuid')
        if not question_paper_uuid:
            return Response(
                {
                    'success': False,
                    'error': 'question_paper_uuid is required'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Process each student group
        results = []
        errors = []
        
        s3_bucket = json_data['s3_info']['bucket']
        s3_job_folder = json_data['s3_info']['job_folder']
        
        for student_group in json_data['student_groups']:
            try:
                roll_number = student_group['roll_number']
                page_names = student_group['page_names']
                
                # Generate S3 URLs for each page
                image_urls = []
                for page_name in page_names:
                    s3_url = f"https://{s3_bucket}.s3.amazonaws.com/{s3_job_folder}{page_name}"
                    image_urls.append(s3_url)
                
                # Check if answer script already exists
                existing_script = AnswerScript.objects.filter(
                    roll_no=roll_number,
                    question_paper_uuid=question_paper_uuid
                ).first()
                
                if existing_script:
                    # Update existing record
                    existing_script.image_urls = image_urls
                    existing_script.save()
                    
                    results.append({
                        'roll_number': roll_number,
                        'action': 'updated',
                        'image_count': len(image_urls),
                        'id': existing_script.id
                    })
                else:
                    # Create new record
                    answer_script = AnswerScript.objects.create(
                        question_paper_uuid=question_paper_uuid,
                        roll_no=roll_number,
                        image_urls=image_urls
                    )
                    
                    results.append({
                        'roll_number': roll_number,
                        'action': 'created',
                        'image_count': len(image_urls),
                        'id': answer_script.id
                    })
                    
            except Exception as e:
                errors.append({
                    'roll_number': student_group.get('roll_number', 'unknown'),
                    'error': str(e)
                })
        
        return Response(
            {
                'success': True,
                'message': f'Processed {len(results)} student groups',
                'results': results,
                'errors': errors,
                'total_processed': len(results),
                'total_errors': len(errors)
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Failed to process extraction results: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )