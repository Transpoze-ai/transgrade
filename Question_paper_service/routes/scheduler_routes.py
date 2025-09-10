from flask import Blueprint, jsonify, request
import uuid as uuid_module
import logging
from datetime import datetime

from services.scheduler_service import SchedulerService

logger = logging.getLogger(__name__)

# Create Blueprint for scheduler routes
scheduler_bp = Blueprint('scheduler', __name__)

# Initialize service
scheduler_service = SchedulerService()

@scheduler_bp.route('/generate-rubric-from-uuid', methods=['POST'])
def generate_rubric_from_uuid():
    """
    Generate rubric by fetching data from database using UUID,
    processing page by page, and then calling the process-rubric API to update the database.
    """
    try:
        # Get UUID from request
        data = request.get_json()
        logger.info(f"Received request data: {data}")
        
        if not data or 'question_paper_uuid' not in data:
            logger.error("Missing question_paper_uuid in request body")
            return jsonify({
                'success': False,
                'error': 'question_paper_uuid is required in request body'
            }), 400
        
        question_paper_uuid = data['question_paper_uuid']
        logger.info(f"Processing rubric generation for UUID: {question_paper_uuid}")
        
        # Validate UUID format
        try:
            uuid_obj = uuid_module.UUID(question_paper_uuid)
            logger.info(f"Valid UUID format confirmed: {uuid_obj}")
        except ValueError:
            logger.error(f"Invalid UUID format: {question_paper_uuid}")
            return jsonify({
                'success': False,
                'error': 'Invalid UUID format'
            }), 400
        
        # Call the service to handle the rubric generation
        result = scheduler_service.process_rubric_generation(question_paper_uuid)
        
        # Return appropriate response based on result
        if result['success']:
            if result.get('database_update', {}).get('success', False):
                return jsonify({
                    'success': True,
                    'message': 'Rubric generation and database update completed successfully',
                    'question_paper_uuid': str(question_paper_uuid),
                    'vlm_description_source': result.get('vlm_description_source', 'unknown'),
                    'processing_summary': result['processing_summary'],
                    'rubric_data': result.get('rubric_data'),
                    'database_update': result['database_update'],
                    'sample_structure': result.get('sample_structure')
                })
            else:
                return jsonify({
                    'success': True,  # Rubric generation was successful
                    'message': 'Rubric generation completed but database update failed',
                    'question_paper_uuid': str(question_paper_uuid),
                    'vlm_description_source': result.get('vlm_description_source', 'unknown'),
                    'processing_summary': result['processing_summary'],
                    'rubric_data': result.get('rubric_data'),
                    'database_update': result['database_update'],
                    'sample_structure': result.get('sample_structure')
                }), 207  # 207 Multi-Status: partial success
        else:
            # Check if it's a client error (4xx) or server error (5xx)
            status_code = 404 if 'not found' in result['error'].lower() else 400 if 'required' in result['error'].lower() else 500
            return jsonify({
                'success': False,
                'error': result['error'],
                'details': result.get('details')
            }), status_code
        
    except Exception as e:
        logger.error(f"Rubric generation failed with exception: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Rubric generation failed: {str(e)}'
        }), 500

@scheduler_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for scheduler service"""
    try:
        health_status = scheduler_service.check_health()
        return jsonify(health_status)
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Health check failed',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@scheduler_bp.route('/status', methods=['GET'])
def service_status():
    """Detailed service status endpoint"""
    try:
        status = scheduler_service.get_service_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Status check failed: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@scheduler_bp.errorhandler(404)
def scheduler_not_found(error):
    """Handle 404 errors for scheduler blueprint"""
    return jsonify({
        'success': False,
        'error': 'Scheduler endpoint not found',
        'available_endpoints': [
            'POST /scheduler/generate-rubric-from-uuid',
            'GET /scheduler/health',
            'GET /scheduler/status'
        ]
    }), 404

@scheduler_bp.errorhandler(500)
def scheduler_internal_error(error):
    """Handle 500 errors for scheduler blueprint"""
    logger.error(f'Scheduler internal server error: {str(error)}')
    return jsonify({
        'success': False,
        'error': 'Internal server error in scheduler service'
    }), 500