import os
import time
import uuid
import zipfile
import threading
import shutil
import gc
import logging
from pdf2image import convert_from_path
from PIL import Image
from PyPDF2 import PdfReader
from werkzeug.utils import secure_filename

from config import Config
from services.s3_service import S3Service

logger = logging.getLogger(__name__)

class PDFService:
    """Service for handling PDF to image conversion operations"""
    
    def __init__(self):
        self.s3_service = S3Service()
        self.conversion_jobs = {}
    
    def create_job(self, job_uuid, pdf_file, dpi=None, img_format=None, quality=None, upload_to_s3=True):
        """Create a new PDF conversion job"""
        # Set defaults
        dpi = dpi or Config.DEFAULT_DPI
        img_format = img_format or Config.DEFAULT_FORMAT
        quality = quality or Config.DEFAULT_QUALITY
        
        # Validate parameters
        if img_format not in ['JPEG', 'PNG']:
            raise ValueError('Format must be JPEG or PNG')
        
        if not (1 <= quality <= 100):
            raise ValueError('Quality must be between 1 and 100')
        
        if upload_to_s3 and not self.s3_service.is_configured():
            raise Exception('S3 not configured. Set AWS credentials and bucket name.')
        
        # Save uploaded file
        os.makedirs(Config.TEMP_DIR, exist_ok=True)
        filename = secure_filename(f"{job_uuid}_question_paper.pdf")
        pdf_path = os.path.join(Config.TEMP_DIR, filename)
        pdf_file.save(pdf_path)
        
        # Initialize job
        self.conversion_jobs[job_uuid] = {
            'status': 'queued',
            'progress': 0,
            'pdf_path': pdf_path,
            'created_at': time.time(),
            'upload_to_s3': upload_to_s3,
            'type': 'question_paper',
            'parameters': {
                'dpi': dpi,
                'format': img_format,
                'quality': quality
            },
            's3_folder': f"s3://{self.s3_service.bucket}/question-paper/{job_uuid}/" if upload_to_s3 else None
        }
        
        # Start conversion in background
        thread = threading.Thread(
            target=self._convert_pdf_to_images,
            args=(pdf_path, job_uuid, dpi, img_format, quality, upload_to_s3)
        )
        thread.daemon = True
        thread.start()
        
        logger.info(f"Created PDF conversion job {job_uuid}")
        return job_uuid
    
    def _convert_pdf_to_images(self, pdf_path, job_id, dpi, img_format, quality, upload_to_s3):
        """Convert PDF to images in background thread"""
        try:
            self.conversion_jobs[job_id]['status'] = 'processing'
            self.conversion_jobs[job_id]['progress'] = 0
            
            output_folder = os.path.join(Config.TEMP_DIR, f"{job_id}_question_paper_images")
            os.makedirs(output_folder, exist_ok=True)
            
            # Get total page count
            total_pages = self._get_pdf_page_count(pdf_path)
            if total_pages:
                self.conversion_jobs[job_id]['total_pages'] = total_pages
            
            start_time = time.time()
            processed_pages = 0
            page_start = 1
            s3_urls = []
            
            # Process PDF in batches
            while True:
                try:
                    # Convert batch
                    pages = convert_from_path(
                        pdf_path,
                        dpi=dpi,
                        first_page=page_start,
                        last_page=page_start + Config.BATCH_SIZE - 1,
                        fmt=img_format,
                        thread_count=2
                    )
                    
                    if not pages:
                        break
                    
                    # Save images and upload to S3
                    for i, page in enumerate(pages):
                        page_num = page_start + i
                        filename = f"page_{page_num:04d}.{img_format.lower()}"
                        filepath = os.path.join(output_folder, filename)
                        
                        # Save image with appropriate format and quality
                        self._save_image(page, filepath, img_format, quality)
                        
                        # Upload to S3 if enabled
                        if upload_to_s3 and self.s3_service.is_configured():
                            try:
                                content_type = 'image/jpeg' if img_format == 'JPEG' else 'image/png'
                                s3_url = self.s3_service.upload_question_paper_file(
                                    filepath, job_id, filename, content_type
                                )
                                s3_urls.append({
                                    'page': page_num,
                                    'filename': filename,
                                    'url': s3_url,
                                    's3_key': f"question-paper/{job_id}/{filename}"
                                })
                            except Exception as s3_error:
                                logger.error(f"S3 upload failed for {filename}: {s3_error}")
                                # Continue processing even if S3 upload fails
                        
                        processed_pages += 1
                        
                        # Update progress
                        if total_pages:
                            progress = int((processed_pages / total_pages) * 90)  # 90% for processing
                            self.conversion_jobs[job_id]['progress'] = progress
                    
                    # Clear memory
                    for page in pages:
                        page.close()
                    del pages
                    gc.collect()
                    
                    page_start += Config.BATCH_SIZE
                    
                except Exception as e:
                    if "Image list is empty" in str(e):
                        break
                    else:
                        raise e
            
            # Update progress to 95% before creating ZIP
            self.conversion_jobs[job_id]['progress'] = 95
            
            # Create ZIP file
            zip_path = self._create_zip_file(output_folder, job_id)
            
            # Upload ZIP and original PDF to S3 if enabled
            zip_s3_url = None
            original_pdf_s3_url = None
            
            if upload_to_s3 and self.s3_service.is_configured():
                try:
                    zip_s3_url = self.s3_service.upload_question_paper_file(
                        zip_path, job_id, f"{job_id}_question_paper_images.zip", 'application/zip'
                    )
                    original_pdf_s3_url = self.s3_service.upload_question_paper_file(
                        pdf_path, job_id, "original.pdf", 'application/pdf'
                    )
                except Exception as s3_error:
                    logger.error(f"S3 upload failed for ZIP/PDF: {s3_error}")
            
            # Update job status
            elapsed_time = time.time() - start_time
            self.conversion_jobs[job_id].update({
                'status': 'completed',
                'progress': 100,
                'processed_pages': processed_pages,
                'elapsed_time': round(elapsed_time, 2),
                'zip_path': zip_path,
                'output_folder': output_folder,
                's3_uploaded': upload_to_s3 and len(s3_urls) > 0,
                's3_images': s3_urls,
                'zip_s3_url': zip_s3_url,
                'original_pdf_s3_url': original_pdf_s3_url
            })
            
            # Clean up local folder (keep ZIP for local download)
            if os.path.exists(output_folder):
                shutil.rmtree(output_folder)
            
            logger.info(f"Successfully completed PDF conversion job {job_id}")
            
        except Exception as e:
            logger.error(f"PDF conversion failed for job {job_id}: {str(e)}")
            self.conversion_jobs[job_id].update({
                'status': 'error',
                'error': str(e)
            })
    
    def _get_pdf_page_count(self, pdf_path):
        """Get total number of pages in PDF"""
        try:
            reader = PdfReader(pdf_path)
            return len(reader.pages)
        except Exception as e:
            logger.warning(f"Could not get page count for {pdf_path}: {e}")
            return None
    
    def _save_image(self, page, filepath, img_format, quality):
        """Save PIL Image with appropriate format and quality"""
        if img_format == 'JPEG':
            page.save(filepath, 'JPEG', quality=quality, optimize=True)
        else:
            page.save(filepath, img_format, optimize=True)
    
    def _create_zip_file(self, output_folder, job_id):
        """Create ZIP file from output folder"""
        zip_path = os.path.join(Config.TEMP_DIR, f"{job_id}_question_paper_images.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(output_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, file)
        
        return zip_path
    
    def get_job_status(self, job_id):
        """Get job status"""
        if job_id not in self.conversion_jobs:
            return None
        
        job = self.conversion_jobs[job_id].copy()
        
        # Remove sensitive file paths from response
        job.pop('pdf_path', None)
        job.pop('zip_path', None)
        job.pop('output_folder', None)
        
        return job
    
    def get_download_path(self, job_id):
        """Get ZIP download path for completed job"""
        if job_id not in self.conversion_jobs:
            return None
        
        job = self.conversion_jobs[job_id]
        if job['status'] != 'completed':
            return None
        
        zip_path = job.get('zip_path')
        if zip_path and os.path.exists(zip_path):
            return zip_path
        
        return None
    
    def get_s3_info(self, job_id):
        """Get S3 information for a job"""
        if job_id not in self.conversion_jobs:
            return None
        
        job = self.conversion_jobs[job_id]
        if job['status'] != 'completed' or not job.get('s3_uploaded'):
            return None
        
        return {
            'job_id': job_id,
            'type': 'question_paper',
            's3_folder': job.get('s3_folder'),
            'zip_s3_url': job.get('zip_s3_url'),
            'original_pdf_s3_url': job.get('original_pdf_s3_url'),
            's3_images': job.get('s3_images', []),
            'total_images': len(job.get('s3_images', []))
        }
    
    def cleanup_job(self, job_id):
        """Clean up local job files"""
        if job_id not in self.conversion_jobs:
            return False
        
        job = self.conversion_jobs[job_id]
        
        try:
            # Clean up local files
            pdf_path = job.get('pdf_path')
            zip_path = job.get('zip_path')
            output_folder = job.get('output_folder')
            
            if pdf_path and os.path.exists(pdf_path):
                os.remove(pdf_path)
            if zip_path and os.path.exists(zip_path):
                os.remove(zip_path)
            if output_folder and os.path.exists(output_folder):
                shutil.rmtree(output_folder)
            
            # Remove from jobs
            del self.conversion_jobs[job_id]
            
            logger.info(f"Cleaned up local files for job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Local cleanup failed for job {job_id}: {e}")
            return False
    
    def cleanup_s3_job(self, job_id):
        """Clean up S3 files for a job"""
        if job_id not in self.conversion_jobs:
            return None
        
        job = self.conversion_jobs[job_id]
        if not job.get('s3_uploaded'):
            return None
        
        try:
            deleted_keys = self.s3_service.cleanup_job_files(job_id)
            logger.info(f"Cleaned up S3 files for job {job_id}")
            return deleted_keys
        except Exception as e:
            logger.error(f"S3 cleanup failed for job {job_id}: {e}")
            raise
    
    def list_jobs(self):
        """List all jobs with their status"""
        jobs_summary = {}
        for job_id, job in self.conversion_jobs.items():
            jobs_summary[job_id] = {
                'status': job['status'],
                'progress': job.get('progress', 0),
                'created_at': job.get('created_at'),
                'processed_pages': job.get('processed_pages', 0),
                'upload_to_s3': job.get('upload_to_s3', False),
                's3_uploaded': job.get('s3_uploaded', False),
                's3_folder': job.get('s3_folder'),
                'type': job.get('type', 'question_paper'),
                'parameters': job.get('parameters', {})
            }
        
        return jobs_summary