from flask import Blueprint, jsonify, request
import logging
from datetime import datetime

from services.vlm_service import VLMService
from config import Config

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
vlm_bp = Blueprint('vlm', __name__)

# Initialize VLM service
vlm_service = VLMService()

@vlm_bp.route('/process-images/<uuid>', methods=['GET'])
def process_images(uuid):
    """Process all images for a given UUID and save to database"""
    try:
        logger.info(f"Processing images for UUID: {uuid}")
        
        # Validate UUID format (basic validation)
        if not uuid or len(uuid) < 10:
            return jsonify({
                'success': False,
                'error': 'Invalid UUID format',
                'message': 'UUID must be at least 10 characters long'
            }), 400
        
        # Check VLM service health
        health_check = vlm_service.check_health()
        if not health_check['success']:
            return jsonify({
                'success': False,
                'error': 'VLM service not properly configured',
                'details': health_check['details']
            }), 500
        
        # Process images with VLM service
        result = vlm_service.process_images_with_database_save(uuid)
        
        if not result['success']:
            return jsonify({
                'success': False,
                'error': result['error'],
                'details': result.get('details', {})
            }), 500
        
        # Return successful response
        return jsonify({
            'success': True,
            'message': 'VLM processing completed and data stored successfully',
            'uuid': uuid,
            'total_pages': result['data']['total_pages'],
            'processing_summary': result['data']['processing_summary'],
            'django_response': result['data']['django_response'],
            'results': result['data']['pages_data']
        })
        
    except Exception as e:
        logger.error(f"Unexpected error processing UUID {uuid}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to process images: {str(e)}'
        }), 500

@vlm_bp.route('/process-images-only/<uuid>', methods=['GET'])
def process_images_only(uuid):
    """Process all images for a given UUID without saving to database (testing endpoint)"""
    try:
        logger.info(f"Processing images only for UUID: {uuid}")
        
        # Validate UUID format (basic validation)
        if not uuid or len(uuid) < 10:
            return jsonify({
                'success': False,
                'error': 'Invalid UUID format',
                'message': 'UUID must be at least 10 characters long'
            }), 400
        
        # Check VLM service health
        health_check = vlm_service.check_health()
        if not health_check['success']:
            return jsonify({
                'success': False,
                'error': 'VLM service not properly configured',
                'details': health_check['details']
            }), 500
        
        # Process images without database save
        result = vlm_service.process_images_only(uuid)
        
        if not result['success']:
            return jsonify({
                'success': False,
                'error': result['error'],
                'details': result.get('details', {})
            }), 500
        
        # Return successful response (original format)
        return jsonify({
            'success': True,
            'uuid': uuid,
            'total_pages': result['data']['total_pages'],
            'results': result['data']['pages_data']
        })
        
    except Exception as e:
        logger.error(f"Unexpected error processing UUID {uuid}: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to process images: {str(e)}'
        }), 500

@vlm_bp.route('/health', methods=['GET'])
def vlm_health_check():
    """VLM service health check endpoint"""
    try:
        health_check = vlm_service.check_health()
        
        return jsonify({
            'success': health_check['success'],
            'service': 'VLM Image Processor',
            'timestamp': datetime.now().isoformat(),
            'details': health_check['details']
        })
        
    except Exception as e:
        logger.error(f"VLM health check failed: {e}")
        return jsonify({
            'success': False,
            'service': 'VLM Image Processor',
            'error': f'Health check failed: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@vlm_bp.route('/debug/s3/<uuid>', methods=['GET'])
def debug_s3_structure(uuid):
    """Debug endpoint to see what's actually in S3"""
    try:
        if not vlm_service.s3_service.is_configured():
            return jsonify({
                'success': False,
                'error': 'S3 client not configured'
            }), 500
            
        debug_info = vlm_service.debug_s3_structure(uuid)
        
        return jsonify({
            'success': True,
            'uuid': uuid,
            'bucket': Config.S3_BUCKET,
            'search_results': debug_info
        })
        
    except Exception as e:
        logger.error(f"S3 debug failed for UUID {uuid}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@vlm_bp.route('/status', methods=['GET'])
def vlm_status():
    """Get VLM service status and configuration"""
    try:
        health_check = vlm_service.check_health()
        
        return jsonify({
            'service': 'VLM Image Processor',
            'version': '1.0.0',
            'status': 'healthy' if health_check['success'] else 'unhealthy',
            'configuration': {
                's3_bucket': Config.S3_BUCKET,
                's3_prefix': vlm_service.question_paper_prefix,
                'openai_model': 'gpt-4o',
                'django_api_url': Config.DJANGO_API_BASE_URL,
                'supported_formats': list(vlm_service.supported_formats)
            },
            'health_details': health_check['details'],
            'endpoints': {
                'process_and_save': 'GET /api/vlm/process-images/<uuid>',
                'process_only': 'GET /api/vlm/process-images-only/<uuid>',
                'health': 'GET /api/vlm/health',
                'status': 'GET /api/vlm/status',
                'debug': 'GET /api/vlm/debug/s3/<uuid>'
            }
        })
        
    except Exception as e:
        logger.error(f"VLM status check failed: {e}")
        return jsonify({
            'success': False,
            'error': f'Status check failed: {str(e)}'
        }), 500

# Error handlers for the blueprint
@vlm_bp.errorhandler(404)
def vlm_not_found(error):
    return jsonify({
        'success': False,
        'error': 'VLM endpoint not found',
        'available_endpoints': {
            'process_and_save': 'GET /api/vlm/process-images/<uuid>',
            'process_only': 'GET /api/vlm/process-images-only/<uuid>',
            'health': 'GET /api/vlm/health',
            'status': 'GET /api/vlm/status',
            'debug': 'GET /api/vlm/debug/s3/<uuid>'
        }
    }), 404

@vlm_bp.errorhandler(500)
def vlm_internal_error(error):
    logger.error(f"VLM internal server error: {str(error)}")
    return jsonify({
        'success': False,
        'error': 'VLM internal server error occurred'
    }), 500