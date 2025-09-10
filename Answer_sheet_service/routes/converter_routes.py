import os
import uuid
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
from config import Config
from services.converter_service import ConverterService
from services.s3_service import S3Service

# Create blueprint
converter_bp = Blueprint('converter', __name__)

# Initialize services
converter_service = ConverterService()
s3_service = S3Service()

@converter_bp.route('/convert', methods=['POST'])
def convert_pdf():
    """
    Convert PDF to images and optionally upload to S3
    
    Form data:
    - pdf_file: PDF file
    - uuid: (optional) Custom UUID for tracking (will be used as S3 folder name)
    - dpi: (optional) Resolution (default: 200)
    - format: (optional) Image format JPEG/PNG (default: JPEG)
    - quality: (optional) JPEG quality 1-100 (default: 85)
    - upload_to_s3: (optional) Whether to upload to S3 (default: true)
    """
    
    # Check if file is present
    if 'pdf_file' not in request.files:
        return jsonify({'error': 'No PDF file provided'}), 400
    
    file = request.files['pdf_file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'File must be a PDF'}), 400
    
    # Get or generate UUID
    job_uuid = request.form.get('uuid', str(uuid.uuid4()))
    
    # Get conversion parameters
    try:
        dpi = int(request.form.get('dpi', Config.DEFAULT_DPI))
        img_format = request.form.get('format', Config.DEFAULT_FORMAT).upper()
        quality = int(request.form.get('quality', Config.DEFAULT_QUALITY))
        upload_to_s3 = request.form.get('upload_to_s3', 'true').lower() == 'true'
    except ValueError:
        return jsonify({'error': 'Invalid parameter values'}), 400
    
    # Validate parameters
    if img_format not in ['JPEG', 'PNG']:
        return jsonify({'error': 'Format must be JPEG or PNG'}), 400
    
    if not (1 <= quality <= 100):
        return jsonify({'error': 'Quality must be between 1 and 100'}), 400
    
    # Check S3 configuration if upload is requested
    if upload_to_s3 and not s3_service.is_configured():
        return jsonify({'error': 'S3 not configured. Set AWS credentials and bucket name.'}), 400
    
    # Save uploaded file
    os.makedirs(Config.TEMP_DIR, exist_ok=True)
    filename = secure_filename(f"{job_uuid}.pdf")
    pdf_path = os.path.join(Config.TEMP_DIR, filename)
    file.save(pdf_path)
    
    # Start conversion
    converter_service.start_conversion(
        pdf_path, job_uuid, dpi, img_format, quality, upload_to_s3
    )
    
    response_data = {
        'message': 'Conversion started',
        'job_id': job_uuid,
        'status': 'queued',
        'upload_to_s3': upload_to_s3
    }
    
    if upload_to_s3:
        response_data['s3_folder'] = f"s3://{Config.S3_BUCKET}/{job_uuid}/"
    
    return jsonify(response_data), 202

@converter_bp.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """Get conversion status"""
    job_status = converter_service.get_job_status(job_id)
    
    if job_status is None:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(job_status)

@converter_bp.route('/download/<job_id>', methods=['GET'])
def download_images(job_id):
    """Download converted images as ZIP (local backup)"""
    job = converter_service.get_job(job_id)
    
    if job is None:
        return jsonify({'error': 'Job not found'}), 404
    
    if job['status'] != 'completed':
        return jsonify({'error': 'Conversion not completed'}), 400
    
    zip_path = job.get('zip_path')
    if not zip_path or not os.path.exists(zip_path):
        return jsonify({'error': 'Download file not found'}), 404
    
    return send_file(
        zip_path,
        as_attachment=True,
        download_name=f'{job_id}_images.zip',
        mimetype='application/zip'
    )

@converter_bp.route('/s3-info/<job_id>', methods=['GET'])
def get_s3_info(job_id):
    """Get S3 information for a job"""
    s3_info = converter_service.get_s3_info(job_id)
    
    if s3_info is None:
        return jsonify({'error': 'Job not found'}), 404
    
    if 'error' in s3_info:
        return jsonify(s3_info), 400
    
    return jsonify(s3_info)

@converter_bp.route('/cleanup/<job_id>', methods=['DELETE'])
def cleanup_job(job_id):
    """Clean up job files (local only - S3 files remain)"""
    result = converter_service.cleanup_local_files(job_id)
    
    if not result['success']:
        return jsonify({'error': result['error']}), 404 if 'not found' in result['error'] else 500
    
    return jsonify({
        'message': result['message'],
        'note': result.get('note', '')
    })

@converter_bp.route('/cleanup-s3/<job_id>', methods=['DELETE'])
def cleanup_s3_job(job_id):
    """Clean up S3 files for a job"""
    result = converter_service.cleanup_s3_files(job_id)
    
    if not result['success']:
        return jsonify({'error': result['error']}), 400
    
    return jsonify({
        'message': result['message'],
        'deleted_objects': result.get('deleted_objects', [])
    })

@converter_bp.route('/jobs', methods=['GET'])
def list_jobs():
    """List all jobs with their status"""
    jobs_summary = converter_service.get_all_jobs_summary()
    return jsonify(jobs_summary)

@converter_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    jobs_summary = converter_service.get_all_jobs_summary()
    return jsonify({
        'status': 'healthy', 
        'active_jobs': len(jobs_summary),
        's3_configured': s3_service.is_configured(),
        's3_bucket': Config.S3_BUCKET if s3_service.is_configured() else None
    })

@converter_bp.route('/s3-config', methods=['GET'])
def s3_config():
    """Get S3 configuration status"""
    return jsonify(s3_service.get_config_info())