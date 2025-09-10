import uuid
from flask import Blueprint, request, jsonify
from services.ocr_service import OCRService

# Create blueprint
ocr_bp = Blueprint('ocr', __name__)

# Initialize service
ocr_service = OCRService()

@ocr_bp.route('/ocr/roll/<roll_no>/uuid/<question_paper_uuid>', methods=['POST'])
def perform_ocr_by_roll_uuid(roll_no, question_paper_uuid):
    """
    Perform OCR on answer script images by roll number and UUID
    """
    try:
        # Validate UUID format
        try:
            uuid.UUID(question_paper_uuid)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid UUID format'
            }), 400

        # Get request parameters
        request_data = request.get_json() if request.is_json else {}
        word_level = request_data.get('word_level', False)
        process_all = request_data.get('process_all', True)
        image_indices = request_data.get('image_indices', [])

        # Process OCR
        result = ocr_service.process_answer_sheet_ocr(
            roll_no, 
            question_paper_uuid, 
            word_level=word_level,
            process_all=process_all,
            image_indices=image_indices
        )

        if result['success']:
            return jsonify(result)
        else:
            status_code = 404 if 'not found' in result.get('error', '').lower() else 500
            return jsonify(result), status_code

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'OCR processing failed: {str(e)}',
            'roll_no': roll_no,
            'question_paper_uuid': question_paper_uuid
        }), 500

@ocr_bp.route('/ocr/test-django', methods=['GET'])
def test_django_connection():
    """Test connection to Django API"""
    try:
        from config import Config
        import requests
        from datetime import datetime
        
        url = f"{Config.DJANGO_API_BASE}/"
        response = requests.get(url, timeout=10)
        
        return jsonify({
            'success': True,
            'django_api_status': response.status_code,
            'django_api_url': url,
            'response_preview': str(response.content[:200]) + '...' if len(response.content) > 200 else str(response.content),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to connect to Django API: {str(e)}',
            'django_api_url': f"{Config.DJANGO_API_BASE}/",
            'timestamp': datetime.now().isoformat()
        }), 500