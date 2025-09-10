import os
import zipfile
import threading
import shutil
import time
import gc
from pdf2image import convert_from_path
from PIL import Image
from PyPDF2 import PdfReader
from config import Config
from services.s3_service import S3Service

class ConverterService:
    def __init__(self):
        self.conversion_jobs = {}
        self.s3_service = S3Service()
    
    def start_conversion(self, pdf_path, job_id, dpi=None, img_format=None, quality=None, upload_to_s3=True):
        """
        Start PDF to images conversion in background
        
        Args:
            pdf_path (str): Path to PDF file
            job_id (str): Unique job identifier
            dpi (int): Resolution for conversion
            img_format (str): Output image format (JPEG/PNG)
            quality (int): JPEG quality (1-100)
            upload_to_s3 (bool): Whether to upload to S3
        """
        # Use default values if not provided
        dpi = dpi or Config.DEFAULT_DPI
        img_format = img_format or Config.DEFAULT_FORMAT
        quality = quality or Config.DEFAULT_QUALITY
        
        # Initialize job
        self.conversion_jobs[job_id] = {
            'status': 'queued',
            'progress': 0,
            'pdf_path': pdf_path,
            'created_at': time.time(),
            'upload_to_s3': upload_to_s3,
            's3_folder': f"s3://{Config.S3_BUCKET}/{job_id}/" if upload_to_s3 else None
        }
        
        # Start conversion in background
        thread = threading.Thread(
            target=self._convert_pdf_to_images,
            args=(pdf_path, job_id, dpi, img_format, quality, upload_to_s3)
        )
        thread.daemon = True
        thread.start()
    
    def _convert_pdf_to_images(self, pdf_path, job_id, dpi, img_format, quality, upload_to_s3):
        """
        Convert PDF to images efficiently in background and upload to S3
        """
        try:
            self.conversion_jobs[job_id]['status'] = 'processing'
            self.conversion_jobs[job_id]['progress'] = 0
            
            output_folder = os.path.join(Config.TEMP_DIR, f"{job_id}_images")
            os.makedirs(output_folder, exist_ok=True)
            
            # Get total page count
            try:
                reader = PdfReader(pdf_path)
                total_pages = len(reader.pages)
                self.conversion_jobs[job_id]['total_pages'] = total_pages
            except:
                total_pages = None
                
            start_time = time.time()
            processed_pages = 0
            page_start = 1
            s3_urls = []
            
            while True:
                try:
                    # Convert batch
                    pages = convert_from_path(
                        pdf_path,
                        dpi=dpi,
                        first_page=page_start,
                        last_page=page_start + Config.BATCH_SIZE - 1,
                        fmt=img_format,
                        thread_count=Config.THREAD_COUNT
                    )
                    
                    if not pages:
                        break
                        
                    # Save images and upload to S3
                    for i, page in enumerate(pages):
                        page_num = page_start + i
                        filename = f"page_{page_num:04d}.{img_format.lower()}"
                        filepath = os.path.join(output_folder, filename)
                        
                        if img_format == 'JPEG':
                            page.save(filepath, 'JPEG', quality=quality, optimize=True)
                            content_type = 'image/jpeg'
                        else:
                            page.save(filepath, img_format, optimize=True)
                            content_type = 'image/png'
                        
                        # Upload to S3 if enabled
                        if upload_to_s3 and self.s3_service.is_configured():
                            try:
                                s3_key = f"{job_id}/{filename}"
                                s3_url = self.s3_service.upload_file(filepath, s3_key, content_type)
                                s3_urls.append({
                                    'page': page_num,
                                    'filename': filename,
                                    'url': s3_url,
                                    's3_key': s3_key
                                })
                            except Exception as s3_error:
                                print(f"S3 upload failed for {filename}: {s3_error}")
                                # Continue processing even if S3 upload fails
                        
                        processed_pages += 1
                        
                        if total_pages:
                            progress = int((processed_pages / total_pages) * 90)  # 90% for processing, 10% for zip
                            self.conversion_jobs[job_id]['progress'] = progress
                    
                    # Clear memory
                    for page in pages:
                        page.close()
                    del pages
                    gc.collect()
                    
                    page_start += Config.BATCH_SIZE
                    
                except Exception as e:
                    if "Image list is empty" in str(e) or not pages:
                        break
                    else:
                        raise e
            
            # Update progress to 95% before creating ZIP
            self.conversion_jobs[job_id]['progress'] = 95
            
            # Create ZIP file (for backup/alternative download)
            zip_path = os.path.join(Config.TEMP_DIR, f"{job_id}_images.zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(output_folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, file)
            
            # Upload ZIP to S3 if enabled
            zip_s3_url = None
            if upload_to_s3 and self.s3_service.is_configured():
                try:
                    zip_s3_key = f"{job_id}/{job_id}_images.zip"
                    zip_s3_url = self.s3_service.upload_file(zip_path, zip_s3_key, 'application/zip')
                except Exception as s3_error:
                    print(f"S3 upload failed for ZIP: {s3_error}")
            
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
                's3_folder': f"s3://{Config.S3_BUCKET}/{job_id}/" if upload_to_s3 else None
            })
            
            # Clean up local folder (keep ZIP for local download option)
            if os.path.exists(output_folder):
                shutil.rmtree(output_folder)
            
        except Exception as e:
            self.conversion_jobs[job_id].update({
                'status': 'error',
                'error': str(e)
            })
    
    def get_job_status(self, job_id):
        """Get job status by ID"""
        if job_id not in self.conversion_jobs:
            return None
        
        job = self.conversion_jobs[job_id].copy()
        
        # Remove sensitive file paths from response
        job.pop('pdf_path', None)
        job.pop('zip_path', None)
        job.pop('output_folder', None)
        
        return job
    
    def get_job(self, job_id):
        """Get complete job data by ID"""
        return self.conversion_jobs.get(job_id)
    
    def cleanup_local_files(self, job_id):
        """Clean up local files for a job"""
        if job_id not in self.conversion_jobs:
            return {'success': False, 'error': 'Job not found'}
        
        job = self.conversion_jobs[job_id]
        
        # Clean up local files only
        pdf_path = job.get('pdf_path')
        zip_path = job.get('zip_path')
        output_folder = job.get('output_folder')
        
        try:
            if pdf_path and os.path.exists(pdf_path):
                os.remove(pdf_path)
            if zip_path and os.path.exists(zip_path):
                os.remove(zip_path)
            if output_folder and os.path.exists(output_folder):
                shutil.rmtree(output_folder)
            
            # Remove from jobs
            del self.conversion_jobs[job_id]
            
            return {
                'success': True,
                'message': 'Local files cleaned up successfully',
                'note': 'S3 files remain unchanged'
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Cleanup failed: {str(e)}'}
    
    def cleanup_s3_files(self, job_id):
        """Clean up S3 files for a job"""
        if job_id not in self.conversion_jobs:
            return {'success': False, 'error': 'Job not found'}
        
        job = self.conversion_jobs[job_id]
        
        if not job.get('s3_uploaded') or not self.s3_service.is_configured():
            return {'success': False, 'error': 'No S3 files to clean up'}
        
        try:
            result = self.s3_service.delete_objects(job_id)
            return {
                'success': True,
                'message': f'Deleted {result["deleted_count"]} S3 objects',
                'deleted_objects': result.get('deleted_objects', [])
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_all_jobs_summary(self):
        """Get summary of all jobs"""
        jobs_summary = {}
        for job_id, job in self.conversion_jobs.items():
            jobs_summary[job_id] = {
                'status': job['status'],
                'progress': job.get('progress', 0),
                'created_at': job.get('created_at'),
                'processed_pages': job.get('processed_pages', 0),
                'upload_to_s3': job.get('upload_to_s3', False),
                's3_uploaded': job.get('s3_uploaded', False),
                's3_folder': job.get('s3_folder')
            }
        
        return jobs_summary
    
    def get_s3_info(self, job_id):
        """Get S3 information for a job"""
        if job_id not in self.conversion_jobs:
            return None
        
        job = self.conversion_jobs[job_id]
        
        if job['status'] != 'completed':
            return {'error': 'Conversion not completed'}
        
        if not job.get('s3_uploaded'):
            return {'error': 'Images not uploaded to S3'}
        
        return {
            'job_id': job_id,
            's3_folder': job.get('s3_folder'),
            'zip_s3_url': job.get('zip_s3_url'),
            's3_images': job.get('s3_images', []),
            'total_images': len(job.get('s3_images', []))
        }