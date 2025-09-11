from flask import Blueprint, jsonify, request
from datetime import datetime
from services.stamp_service import StampService
import traceback

# Create blueprint
stamp_bp = Blueprint('stamp', __name__)

# Initialize stamp service
stamp_service = StampService()

@stamp_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for stamp detection service"""
    return jsonify({
        'status': 'healthy',
        'service': 'stamp_detection',
        'timestamp': datetime.now().isoformat(),
        'api_key_configured': stamp_service.is_openai_configured(),
        's3_client_available': stamp_service.is_s3_configured(),
        'bucket_name': stamp_service.get_s3_bucket_name()
    })

@stamp_bp.route('/process-stamps/<job_id>', methods=['POST'])
def process_stamps_from_s3(job_id: str):
    """Main endpoint to process images from S3 for stamp detection and roll number extraction"""
    
    try:
        print(f"🚀 Starting processing for job: {job_id}")
        
        # Get optional parameters from request
        request_data = request.get_json() if request.is_json else {}
        webhook_url = request_data.get('webhook_url')
        crop_percentage = request_data.get('crop_percentage', 0.2)
        
        # Process the job
        result = stamp_service.process_job(
            job_id=job_id,
            webhook_url=webhook_url,
            crop_percentage=crop_percentage
        )
        
        print(f"🎉 Processing completed for job: {job_id}")
        return jsonify(result)

    except Exception as e:
        # Handle errors
        error_response = stamp_service.create_error_response(job_id, str(e))
        
        print(f"❌ Processing failed for job: {job_id} - Error: {str(e)}")
        traceback.print_exc()
        
        return jsonify(error_response), 500

@stamp_bp.route('/config', methods=['GET'])
def get_stamp_config():
    """Get stamp detection service configuration"""
    return jsonify({
        'service': 'stamp_detection',
        'openai_configured': stamp_service.is_openai_configured(),
        's3_configured': stamp_service.is_s3_configured(),
        's3_bucket': stamp_service.get_s3_bucket_name(),
        'temp_folder': stamp_service.get_temp_folder(),
        'supported_extensions': stamp_service.get_allowed_extensions(),
        'default_webhook_url': stamp_service.get_default_webhook_url()
    })

@stamp_bp.route('/test-vlm', methods=['POST'])
def test_vlm_extraction():
    """Test VLM extraction with a sample image URL"""
    try:
        data = request.get_json()
        if not data or 'image_url' not in data:
            return jsonify({'error': 'image_url is required'}), 400
        
        image_url = data['image_url']
        crop_percentage = data.get('crop_percentage', 0.2)
        
        # Test the VLM extraction
        result = stamp_service.test_vlm_extraction(image_url, crop_percentage)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'test_status': 'failed'
        }), 500