import requests
import time
import io
import logging
from PIL import Image
from datetime import datetime
import uuid as uuid_module

from config import Config
from services.s3_service import S3Service

logger = logging.getLogger(__name__)

class OCRService:
    """Service for handling OCR processing using Azure Cognitive Services"""
    
    def __init__(self):
        self.s3_service = S3Service()
        self.azure_config = Config.get_azure_config()
        self.django_config = Config.get_django_config()
        
        # Azure OCR configuration
        self.subscription_key = self.azure_config['subscription_key']
        self.endpoint = self.azure_config['endpoint']
        self.read_url = self.azure_config['read_url']
        self.limits = self.azure_config['limits']
    
    def is_configured(self):
        """Check if OCR service is properly configured"""
        return bool(self.subscription_key and self.endpoint)
    
    def process_question_paper(self, question_paper_uuid):
        """Process all images for a question paper UUID from S3"""
        try:
            # Validate UUID format
            try:
                uuid_obj = uuid_module.UUID(question_paper_uuid)
            except ValueError:
                raise ValueError('Invalid UUID format')
            
            # Check prerequisites
            if not self.s3_service.is_configured():
                raise Exception('S3 client not configured. Check AWS credentials and settings.')
            
            if not self.is_configured():
                raise Exception('Azure OCR not configured. Check subscription key and endpoint.')
            
            logger.info(f"Starting OCR processing for UUID: {question_paper_uuid}")
            
            # Get all image files from S3
            image_files = self.s3_service.get_question_paper_images(question_paper_uuid)
            
            if not image_files:
                raise Exception(f'No images found in S3 for question paper UUID: {question_paper_uuid}')
            
            logger.info(f"Found {len(image_files)} images to process")
            
            # Process all images
            all_pages_data = []
            processing_results = []
            
            for i, image_file in enumerate(image_files):
                logger.info(f"Processing {i+1}/{len(image_files)}: {image_file['filename']}")
                
                try:
                    # Download image from S3
                    image_data = self.s3_service.download_file(image_file['key'])
                    
                    # Process with OCR
                    ocr_result = self._extract_text_from_image_data(image_data, image_file['filename'])
                    
                    page_result = {
                        'page_number': i + 1,
                        'filename': image_file['filename'],
                        's3_key': image_file['key'],
                        'success': ocr_result['success']
                    }
                    
                    if ocr_result['success']:
                        # Store the complete Azure OCR result for this page
                        page_data = {
                            'page_number': i + 1,
                            'filename': image_file['filename'],
                            's3_key': image_file['key'],
                            'text_lines': ocr_result['text_lines'],
                            'full_text': ocr_result['full_text'],
                            'azure_ocr_result': ocr_result['azure_result']
                        }
                        all_pages_data.append(page_data)
                        
                        page_result['text_lines_count'] = len(ocr_result['text_lines'])
                        page_result['characters_extracted'] = len(ocr_result['full_text'])
                        
                        logger.info(f"Successfully processed {image_file['filename']}: "
                                  f"{len(ocr_result['text_lines'])} lines, {len(ocr_result['full_text'])} characters")
                    else:
                        page_result['error'] = ocr_result['error']
                        logger.error(f"Failed to process {image_file['filename']}: {ocr_result['error']}")
                    
                    processing_results.append(page_result)
                    
                except Exception as e:
                    error_result = {
                        'page_number': i + 1,
                        'filename': image_file['filename'],
                        's3_key': image_file['key'],
                        'success': False,
                        'error': f'Failed to process image: {str(e)}'
                    }
                    processing_results.append(error_result)
                    logger.error(f"Error processing {image_file['filename']}: {str(e)}")
            
            # Prepare OCR data structure
            ocr_json_data = {
                'question_paper_uuid': str(question_paper_uuid),
                'total_pages': len(image_files),
                'processed_pages': len(all_pages_data),
                'processing_timestamp': datetime.now().isoformat(),
                's3_source': f's3://{self.s3_service.bucket}/question-paper/{question_paper_uuid}/',
                'pages_data': all_pages_data,
                'processing_summary': {
                    'successful_pages': len([r for r in processing_results if r['success']]),
                    'failed_pages': len([r for r in processing_results if not r['success']]),
                    'total_text_lines': sum(len(page['text_lines']) for page in all_pages_data),
                    'total_characters': sum(len(page['full_text']) for page in all_pages_data)
                }
            }
            
            logger.info("OCR processing complete. Sending data to Django API...")
            
            # Send data to Django API
            django_result = self._send_ocr_data_to_django(question_paper_uuid, ocr_json_data)
            
            if not django_result['success']:
                logger.error(f"Failed to store data in Django: {django_result['error']}")
                return {
                    'success': False,
                    'error': 'OCR processing completed but failed to store in database',
                    'django_error': django_result['error'],
                    'processing_summary': ocr_json_data['processing_summary'],
                    'individual_page_results': processing_results
                }
            
            # Success response
            logger.info(f"Successfully processed and stored question paper UUID: {question_paper_uuid}")
            return {
                'success': True,
                'message': 'Question paper images processed and data stored successfully',
                'question_paper_uuid': str(question_paper_uuid),
                's3_source': f's3://{self.s3_service.bucket}/question-paper/{question_paper_uuid}/',
                'processing_summary': {
                    'total_images': len(image_files),
                    'successful_pages': len(all_pages_data),
                    'failed_pages': len(image_files) - len(all_pages_data),
                    'total_text_lines': ocr_json_data['processing_summary']['total_text_lines'],
                    'total_characters': ocr_json_data['processing_summary']['total_characters']
                },
                'django_response': django_result['response'],
                'individual_page_results': processing_results
            }
            
        except Exception as e:
            logger.error(f'OCR processing failed for question paper: {str(e)}')
            return {
                'success': False,
                'error': f'Processing failed: {str(e)}'
            }
    
    def _extract_text_from_image_data(self, image_data, filename):
        """Extract text from image data using Azure OCR"""
        try:
            # Prepare image data
            processed_image_data = self._resize_image_for_ocr(image_data, filename)
            
            headers = {
                "Ocp-Apim-Subscription-Key": self.subscription_key,
                "Content-Type": "application/octet-stream"
            }
            
            # Send OCR request
            response = requests.post(
                self.read_url, 
                headers=headers, 
                data=processed_image_data, 
                timeout=Config.AZURE_OCR_TIMEOUT
            )
            
            if response.status_code != 202:
                logger.error(f'OCR request failed for {filename}: {response.status_code} - {response.text}')
                return {
                    'success': False,
                    'error': f'OCR request failed: {response.status_code}',
                    'details': response.text
                }
            
            # Poll for results
            operation_url = response.headers["Operation-Location"]
            
            for attempt in range(30):  # Wait up to 30 seconds
                try:
                    result_response = requests.get(
                        operation_url, 
                        headers={"Ocp-Apim-Subscription-Key": self.subscription_key},
                        timeout=10
                    )
                    result = result_response.json()
                    
                    if result["status"] == "succeeded":
                        break
                    elif result["status"] == "failed":
                        logger.error(f'OCR analysis failed for {filename}')
                        return {'success': False, 'error': 'OCR analysis failed'}
                    
                    time.sleep(1)
                except requests.exceptions.RequestException as e:
                    logger.error(f'OCR polling error for {filename}: {e}')
                    return {'success': False, 'error': f'OCR polling error: {str(e)}'}
            else:
                logger.error(f'OCR polling timeout for {filename}')
                return {'success': False, 'error': 'OCR polling timeout'}
            
            # Extract text from results
            extracted_lines = []
            if "analyzeResult" in result and "readResults" in result["analyzeResult"]:
                for page_result in result["analyzeResult"]["readResults"]:
                    for line in page_result.get("lines", []):
                        extracted_lines.append(line.get("text", ""))
            
            return {
                'success': True,
                'text_lines': extracted_lines,
                'full_text': '\n'.join(extracted_lines),
                'azure_result': result
            }
            
        except Exception as e:
            logger.error(f'OCR processing failed for {filename}: {str(e)}')
            return {'success': False, 'error': f'OCR processing failed: {str(e)}'}
    
    def _resize_image_for_ocr(self, image_data, filename):
        """Resize image to fit Azure OCR requirements"""
        try:
            image = Image.open(io.BytesIO(image_data))
            original_width, original_height = image.size
            original_size = len(image_data)
            
            logger.debug(f"Processing: {filename} - {original_width}x{original_height}, "
                        f"{original_size / (1024*1024):.2f}MB")
            
            # Check if resize is needed
            needs_resize = (
                original_width < self.limits['min_dimension'] or 
                original_height < self.limits['min_dimension'] or 
                original_width > self.limits['max_dimension'] or 
                original_height > self.limits['max_dimension'] or 
                original_size > self.limits['max_file_size']
            )
            
            if not needs_resize:
                return image_data
            
            # Calculate new dimensions
            if (original_width < self.limits['min_dimension'] or 
                original_height < self.limits['min_dimension']):
                scale = max(
                    self.limits['min_dimension'] / original_width, 
                    self.limits['min_dimension'] / original_height
                )
            elif (original_width > self.limits['max_dimension'] or 
                  original_height > self.limits['max_dimension']):
                scale = min(
                    self.limits['max_dimension'] / original_width, 
                    self.limits['max_dimension'] / original_height
                )
            else:
                scale = 0.8  # Reduce size for file size issues
            
            new_width = int(original_width * scale)
            new_height = int(original_height * scale)
            
            # Resize image
            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to RGB if needed
            if resized_image.mode in ('RGBA', 'LA', 'P'):
                rgb_image = Image.new('RGB', resized_image.size, (255, 255, 255))
                if resized_image.mode == 'P':
                    resized_image = resized_image.convert('RGBA')
                rgb_image.paste(
                    resized_image, 
                    mask=resized_image.split()[-1] if resized_image.mode in ('RGBA', 'LA') else None
                )
                resized_image = rgb_image
            
            # Save to bytes with quality adjustment
            output = io.BytesIO()
            quality = 85
            while quality > 30:
                output.seek(0)
                output.truncate()
                resized_image.save(output, format='JPEG', quality=quality, optimize=True)
                if len(output.getvalue()) <= self.limits['max_file_size']:
                    break
                quality -= 10
            
            logger.debug(f"Resized {filename}: {new_width}x{new_height}, "
                        f"{len(output.getvalue()) / (1024*1024):.2f}MB")
            
            return output.getvalue()
            
        except Exception as e:
            raise Exception(f"Error processing image {filename}: {str(e)}")
    
    def _send_ocr_data_to_django(self, question_paper_uuid, ocr_data):
        """Send OCR data to Django API"""
        try:
            payload = {
                "question_paper_uuid": str(question_paper_uuid),
                "ocr_json": ocr_data
            }
            
            headers = {'Content-Type': 'application/json'}
            
            logger.info(f"Sending OCR data to Django API for UUID: {question_paper_uuid}")
            
            response = requests.post(
                self.django_config['process_endpoint'],
                json=payload,
                headers=headers,
                timeout=self.django_config['timeout']
            )
            
            logger.info(f"Django API response: {response.status_code}")
            
            if response.status_code in [200, 201]:
                return {
                    'success': True,
                    'response': response.json(),
                    'status_code': response.status_code
                }
            else:
                logger.error(f'Django API returned {response.status_code}: {response.text}')
                return {
                    'success': False,
                    'error': f'Django API returned {response.status_code}',
                    'response': response.text
                }
                
        except requests.exceptions.Timeout:
            logger.error('Django API request timeout')
            return {'success': False, 'error': 'Django API request timeout'}
        except requests.exceptions.ConnectionError:
            logger.error('Failed to connect to Django API')
            return {'success': False, 'error': 'Failed to connect to Django API - connection error'}
        except requests.exceptions.RequestException as e:
            logger.error(f'Django API request failed: {str(e)}')
            return {'success': False, 'error': f'Failed to connect to Django API: {str(e)}'}
        except Exception as e:
            logger.error(f'Error sending data to Django: {str(e)}')
            return {'success': False, 'error': f'Error sending data to Django: {str(e)}'}
    
    def list_question_paper_images(self, uuid):
        """List all images available for a question paper UUID in S3"""
        try:
            # Validate UUID format
            try:
                uuid_obj = uuid_module.UUID(uuid)
            except ValueError:
                raise ValueError('Invalid UUID format')
            
            # Check S3 client
            if not self.s3_service.is_configured():
                raise Exception('S3 client not configured')
            
            # Get image files
            image_files = self.s3_service.get_question_paper_images(uuid)
            
            return {
                'success': True,
                'question_paper_uuid': uuid,
                's3_path': f's3://{self.s3_service.bucket}/question-paper/{uuid}/',
                'total_images': len(image_files),
                'images': image_files
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to list images: {str(e)}'
            }