from flask import Blueprint, request, jsonify, send_file
import uuid as uuid_module
import os
import logging

from services.pdf_service import PDFService

logger = logging.getLogger(__name__)
pdf_bp = Blueprint('pdf', __name__)

# Initialize PDF service
pdf_service = PDFService()

@pdf_bp.route('/convert', methods=['POST'])
def convert_question_paper():
    """
    Convert Question Paper PDF to images and optionally upload to S3
    
    Form data:
    - pdf_file: PDF file
    - uuid: (required) UUID for tracking (will be used as S3 folder name)
    - dpi: (optional) Resolution (default: 200)
    - format: (optional) Image format JPEG/PNG (default: JPEG)
    - quality: (optional) JPEG quality 1-100 (default: 85)
    - upload_to_s3: (optional) Whether to upload to S3 (default: true)
    """
    try:
        # Check if file is present
        if 'pdf_file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No PDF file provided'
            }), 400
        
        file = request.files['pdf_file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({
                'success': False,
                'error': 'File must be a PDF'
            }), 400
        
        # UUID is required for question papers
        job_uuid = request.form.get('uuid')
        if not job_uuid:
            return jsonify({
                'success': False,
                'error': 'UUID is required for question paper processing'
            }), 400
        
        # Validate UUID format
        try:
            uuid_module.UUID(job_uuid)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid UUID format'
            }), 400
        
        # Get conversion parameters
        dpi = request.form.get('dpi')
        if dpi:
            try:
                dpi = int(dpi)
                if dpi < 72 or dpi > 600:
                    return jsonify({
                        'success': False,
                        'error': 'DPI must be between 72 and 600'
                    }), 400
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'DPI must be a valid integer'
                }), 400
        
        img_format = request.form.get('format', 'JPEG').upper()
        if img_format not in ['JPEG', 'PNG']:
            return jsonify({
                'success': False,
                'error': 'Format must be JPEG or PNG'
            }), 400
        
        quality = request.form.get('quality')
        if quality:
            try:
                quality = int(quality)
                if not (1 <= quality <= 100):
                    return jsonify({
                        'success': False,
                        'error': 'Quality must be between 1 and 100'
                    }), 400
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Quality must be a valid integer'
                }), 400
        
        upload_to_s3 = request.form.get('upload_to_s3', 'true').lower() == 'true'
        
        # Create conversion job
        try:
            job_id = pdf_service.create_job(
                job_uuid, file, dpi, img_format, quality, upload_to_s3
            )
            
            response_data = {
                'success': True,
                'message': 'Question paper conversion started',
                'job_id': job_id,
                'status': 'queued',
                'type': 'question_paper',
                'upload_to_s3': upload_to_s3
            }
            
            if upload_to_s3 and pdf_service.s3_service.is_configured():
                response_data['s3_folder'] = f"s3://{pdf_service.s3_service.bucket}/question-paper/{job_id}/"
            
            logger.info(f"Started PDF conversion job {job_id}")
            return jsonify(response_data), 202
            
        except Exception as e:
            logger.error(f"Failed to create conversion job: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
        
    except Exception as e:
        logger.error(f"PDF conversion request failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Request processing failed: {str(e)}'
        }), 500

@pdf_bp.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """Get conversion status"""
    try:
        # Validate UUID format
        try:
            uuid_module.UUID(job_id)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid job ID format'
            }), 400
        
        job_status = pdf_service.get_job_status(job_id)
        
        if job_status is None:
            return jsonify({
                'success': False,
                'error': 'Job not found'
            }), 404
        
        return jsonify({
            'success': True,
            **job_status
        })
        
    except Exception as e:
        logger.error(f"Status check failed for job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Status check failed: {str(e)}'
        }), 500

@pdf_bp.route('/download/<job_id>', methods=['GET'])
def download_images(job_id):
    """Download converted images as ZIP (local backup)"""
    try:
        # Validate UUID format
        try:
            uuid_module.UUID(job_id)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid job ID format'
            }), 400
        
        zip_path = pdf_service.get_download_path(job_id)
        
        if zip_path is None:
            job_status = pdf_service.get_job_status(job_id)
            if job_status is None:
                return jsonify({
                    'success': False,
                    'error': 'Job not found'
                }), 404
            elif job_status['status'] != 'completed':
                return jsonify({
                    'success': False,
                    'error': 'Conversion not completed',
                    'current_status': job_status['status'],
                    'progress': job_status.get('progress', 0)
                }), 400
            else:
                return jsonify({
                    'success': False,
                    'error': 'Download file not found'
                }), 404
        
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=f'{job_id}_question_paper_images.zip',
            mimetype='application/zip'
        )
        
    except Exception as e:
        logger.error(f"Download failed for job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Download failed: {str(e)}'
        }), 500

@pdf_bp.route('/s3-info/<job_id>', methods=['GET'])
def get_s3_info(job_id):
    """Get S3 information for a job"""
    try:
        # Validate UUID format
        try:
            uuid_module.UUID(job_id)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid job ID format'
            }), 400
        
        s3_info = pdf_service.get_s3_info(job_id)
        
        if s3_info is None:
            job_status = pdf_service.get_job_status(job_id)
            if job_status is None:
                return jsonify({
                    'success': False,
                    'error': 'Job not found'
                }), 404
            elif job_status['status'] != 'completed':
                return jsonify({
                    'success': False,
                    'error': 'Conversion not completed',
                    'current_status': job_status['status']
                }), 400
            else:
                return jsonify({
                    'success': False,
                    'error': 'Images not uploaded to S3'
                }), 400
        
        return jsonify({
            'success': True,
            **s3_info
        })
        
    except Exception as e:
        logger.error(f"S3 info request failed for job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'S3 info request failed: {str(e)}'
        }), 500

@pdf_bp.route('/cleanup/<job_id>', methods=['DELETE'])
def cleanup_job(job_id):
    """Clean up job files (local only - S3 files remain)"""
    try:
        # Validate UUID format
        try:
            uuid_module.UUID(job_id)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid job ID format'
            }), 400
        
        success = pdf_service.cleanup_job(job_id)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Job not found or cleanup failed'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Local files cleaned up successfully',
            'note': 'S3 files remain unchanged'
        })
        
    except Exception as e:
        logger.error(f"Local cleanup failed for job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Cleanup failed: {str(e)}'
        }), 500

@pdf_bp.route('/cleanup-s3/<job_id>', methods=['DELETE'])
def cleanup_s3_job(job_id):
    """Clean up S3 files for a job"""
    try:
        # Validate UUID format
        try:
            uuid_module.UUID(job_id)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid job ID format'
            }), 400
        
        deleted_keys = pdf_service.cleanup_s3_job(job_id)
        
        if deleted_keys is None:
            job_status = pdf_service.get_job_status(job_id)
            if job_status is None:
                return jsonify({
                    'success': False,
                    'error': 'Job not found'
                }), 404
            else:
                return jsonify({
                    'success': False,
                    'error': 'No S3 files to clean up'
                }), 400
        
        return jsonify({
            'success': True,
            'message': f'Deleted {len(deleted_keys)} S3 objects from question-paper folder',
            'deleted_objects': deleted_keys
        })
        
    except Exception as e:
        logger.error(f"S3 cleanup failed for job {job_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'S3 cleanup failed: {str(e)}'
        }), 500

@pdf_bp.route('/jobs', methods=['GET'])
def list_jobs():
    """List all jobs with their status"""
    try:
        jobs = pdf_service.list_jobs()
        return jsonify({
            'success': True,
            'total_jobs': len(jobs),
            'jobs': jobs
        })
        
    except Exception as e:
        logger.error(f"Jobs listing failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to list jobs: {str(e)}'
        }), 500