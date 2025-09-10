from flask import Blueprint, request, jsonify
import uuid as uuid_module
import logging

from services.ocr_service import OCRService

logger = logging.getLogger(__name__)
ocr_bp = Blueprint('ocr', __name__)

# Initialize OCR service
ocr_service = OCRService()

@ocr_bp.route('/process', methods=['POST'])
def process_question_paper():
    """
    Process all images for a question paper UUID from S3 and store results in Django database
    
    JSON body:
    - question_paper_uuid: UUID of the question paper to process
    """
    try:
        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body must be valid JSON'
            }), 400
        
        # Validate required fields
        if 'question_paper_uuid' not in data:
            return jsonify({
                'success': False,
                'error': 'question_paper_uuid is required in request body'
            }), 400
        
        question_paper_uuid = data['question_paper_uuid']
        
        # Validate UUID format
        try:
            uuid_module.UUID(question_paper_uuid)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid UUID format'
            }), 400
        
        # Check service configuration
        if not ocr_service.s3_service.is_configured():
            return jsonify({
                'success': False,
                'error': 'S3 client not configured. Check AWS credentials and settings.'
            }), 500
        
        if not ocr_service.is_configured():
            return jsonify({
                'success': False,
                'error': 'Azure OCR not configured. Check subscription key and endpoint.'
            }), 500
        
        logger.info(f"Starting OCR processing request for UUID: {question_paper_uuid}")
        
        # Process the question paper
        result = ocr_service.process_question_paper(question_paper_uuid)
        
        if result['success']:
            return jsonify(result), 200
        else:
            # Determine appropriate HTTP status code based on error type
            if 'not found' in result['error'].lower():
                status_code = 404
            elif 'not configured' in result['error'].lower():
                status_code = 500
            else:
                status_code = 400
            
            return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"OCR processing request failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Request processing failed: {str(e)}'
        }), 500

@ocr_bp.route('/images/<uuid>', methods=['GET'])
def list_question_paper_images(uuid):
    """List all images available for a question paper UUID in S3"""
    try:
        # Validate UUID format
        try:
            uuid_module.UUID(uuid)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid UUID format'
            }), 400
        
        # Check S3 service configuration
        if not ocr_service.s3_service.is_configured():
            return jsonify({
                'success': False,
                'error': 'S3 client not configured'
            }), 500
        
        logger.info(f"Listing images for UUID: {uuid}")
        
        # Get image list
        result = ocr_service.list_question_paper_images(uuid)
        
        if result['success']:
            return jsonify(result), 200
        else:
            # Determine appropriate HTTP status code
            if 'not found' in result['error'].lower():
                status_code = 404
            elif 'not configured' in result['error'].lower():
                status_code = 500
            else:
                status_code = 400
            
            return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Image listing failed for UUID {uuid}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to list images: {str(e)}'
        }), 500

@ocr_bp.route('/config', methods=['GET'])
def get_ocr_config():
    """Get OCR service configuration status"""
    try:
        config_status = {
            'success': True,
            'azure_ocr': {
                'configured': ocr_service.is_configured(),
                'endpoint': ocr_service.endpoint if ocr_service.is_configured() else None,
                'subscription_key_set': bool(ocr_service.subscription_key),
                'limits': ocr_service.limits
            },
            's3': {
                'configured': ocr_service.s3_service.is_configured(),
                'bucket': ocr_service.s3_service.bucket if ocr_service.s3_service.is_configured() else None,
                'region': ocr_service.s3_service.region,
                'accessible': ocr_service.s3_service.test_connection() if ocr_service.s3_service.is_configured() else False
            },
            'django_api': {
                'configured': bool(ocr_service.django_config['base_url']),
                'endpoint': ocr_service.django_config['process_endpoint'],
                'timeout': ocr_service.django_config['timeout']
            }
        }
        
        return jsonify(config_status), 200
        
    except Exception as e:
        logger.error(f"Configuration status check failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Configuration check failed: {str(e)}'
        }), 500

@ocr_bp.route('/supported-formats', methods=['GET'])
def get_supported_formats():
    """Get list of supported image formats for OCR"""
    try:
        from config import Config
        
        return jsonify({
            'success': True,
            'supported_formats': list(Config.SUPPORTED_EXTENSIONS),
            'azure_limits': {
                'min_dimension': Config.MIN_DIMENSION,
                'max_dimension': Config.MAX_DIMENSION,
                'max_file_size_mb': Config.MAX_FILE_SIZE / (1024 * 1024),
                'max_file_size_bytes': Config.MAX_FILE_SIZE
            },
            'processing_info': {
                'automatic_resizing': True,
                'format_conversion': 'Images are automatically converted to RGB JPEG if needed',
                'quality_adjustment': 'Quality is automatically adjusted to meet size limits'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Supported formats request failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get supported formats: {str(e)}'
        }), 500