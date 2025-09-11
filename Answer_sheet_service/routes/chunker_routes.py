"""
OCR Semantic Chunker Routes
Flask blueprint for handling OCR semantic chunking with LLM analysis
"""

from flask import Blueprint, request, jsonify
from functools import wraps
import logging
import time
from services.chunker_service import ChunkerService
from config import Config

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
chunker_bp = Blueprint('chunker', __name__, url_prefix='/chunker')

def validate_json(required_fields):
    """Validation decorator for JSON requests"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({'error': 'Content-Type must be application/json'}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Request body must be valid JSON'}), 400
            
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return jsonify({'error': f'Missing required fields: {missing_fields}'}), 400
            
            return f(data, *args, **kwargs)
        return decorated_function
    return decorator

@chunker_bp.route('/', methods=['GET'])
def chunker_health():
    """Health check endpoint for chunker service"""
    return jsonify({
        "message": "OCR Semantic Chunker API with LLM Analysis is running",
        "django_url": Config.DJANGO_API_BASE,
        "webhook_url": Config.WEBHOOK_URL,
        "status": "healthy",
        "features": [
            "OCR Processing", 
            "LLM Semantic Analysis", 
            "Intelligent Chunking", 
            "Webhook Notifications"
        ],
        "webhook_configured": Config.WEBHOOK_URL is not None
    })

@chunker_bp.route('/process-ocr-chunks', methods=['POST'])
@validate_json(['question_paper_uuid', 'roll_no', 'openai_api_key'])
def process_ocr_chunks(data):
    """
    Fetch OCR data from Django database and process through semantic chunker with LLM analysis
    
    Expected JSON body:
    {
        "question_paper_uuid": "string",
        "roll_no": "string", 
        "openai_api_key": "string",
        "max_chunk_size": 1500 (optional)
    }
    
    Returns:
        Combined semantic chunks from all pages with LLM-identified boundaries
    """
    try:
        question_paper_uuid = data['question_paper_uuid']
        roll_no = data['roll_no']
        openai_api_key = data['openai_api_key']
        max_chunk_size = data.get('max_chunk_size', 1500)
        
        logger.info(f"Processing OCR chunks for UUID: {question_paper_uuid}, Roll: {roll_no}")
        
        # Initialize chunker service
        chunker_service = ChunkerService()
        
        # Process the chunks
        result = chunker_service.process_ocr_chunks(
            question_paper_uuid=question_paper_uuid,
            roll_no=roll_no,
            openai_api_key=openai_api_key,
            max_chunk_size=max_chunk_size
        )
        
        # Return appropriate response based on result
        if result['success']:
            return jsonify(result), 200
        else:
            status_code = 404 if 'not found' in result.get('error', '').lower() else 500
            return jsonify(result), status_code
            
    except Exception as e:
        logger.error(f"Unexpected error in process_ocr_chunks: {e}")
        return jsonify({
            'success': False,
            'question_paper_uuid': data.get('question_paper_uuid', ''),
            'roll_no': data.get('roll_no', ''),
            'total_pages': 0,
            'total_chunks': 0,
            'chunks': [],
            'page_info': [],
            'error': str(e)
        }), 500

@chunker_bp.route('/test-django-connection', methods=['GET'])
def test_django_connection():
    """Test connection to Django API"""
    try:
        chunker_service = ChunkerService()
        result = chunker_service.test_django_connection()
        
        if result['status'] == 'success':
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "django_url": Config.DJANGO_API_BASE,
            "error": str(e),
            "message": "Django API connection test failed"
        }), 500

@chunker_bp.route('/test-openai', methods=['GET'])
def test_openai():
    """Test OpenAI API connection"""
    api_key = request.args.get('api_key')
    if not api_key:
        return jsonify({
            "status": "error",
            "error": "api_key parameter is required"
        }), 400
    
    try:
        chunker_service = ChunkerService()
        result = chunker_service.test_openai_connection(api_key)
        
        if result['status'] == 'success':
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "message": "OpenAI API test failed"
        }), 400

@chunker_bp.route('/debug/webhook-config', methods=['GET'])
def debug_webhook_config():
    """Debug endpoint to check webhook configuration"""
    return jsonify({
        "webhook_url": Config.WEBHOOK_URL,
        "webhook_timeout": Config.WEBHOOK_TIMEOUT,
        "webhook_max_retries": Config.WEBHOOK_MAX_RETRIES,
        "django_api_base": Config.DJANGO_API_BASE,
        "webhook_configured": Config.WEBHOOK_URL is not None
    })

@chunker_bp.route('/debug/test-webhook', methods=['POST'])
def debug_test_webhook():
    """Debug endpoint to test webhook functionality"""
    try:
        test_data = {
            'success': True,
            'test': True,
            'message': 'This is a test webhook notification',
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'total_chunks': 0,
            'chunks': []
        }
        
        chunker_service = ChunkerService()
        success = chunker_service.send_webhook_notification(Config.WEBHOOK_URL, test_data)
        
        return jsonify({
            'webhook_test': 'completed',
            'webhook_url': Config.WEBHOOK_URL,
            'success': success,
            'test_data_sent': test_data
        })
        
    except Exception as e:
        return jsonify({
            'webhook_test': 'failed',
            'error': str(e),
            'webhook_url': Config.WEBHOOK_URL
        }), 500

# Error handlers specific to chunker blueprint
@chunker_bp.errorhandler(404)
def chunker_not_found(error):
    return jsonify({
        'success': False,
        'error': 'Chunker endpoint not found',
        'message': 'The requested chunker endpoint does not exist'
    }), 404

@chunker_bp.errorhandler(405)
def chunker_method_not_allowed(error):
    return jsonify({
        'success': False,
        'error': 'Method not allowed',
        'message': 'The requested method is not allowed for this chunker endpoint'
    }), 405

@chunker_bp.errorhandler(400)
def chunker_bad_request(error):
    return jsonify({
        'success': False,
        'error': 'Bad request',
        'message': 'The chunker request could not be processed due to invalid syntax or missing data'
    }), 400