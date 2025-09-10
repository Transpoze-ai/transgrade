import boto3
import base64
import os
import logging
import json
import requests
import time
import re
from typing import List, Dict, Optional
from botocore.exceptions import ClientError, NoCredentialsError
from openai import OpenAI

from config import Config
from services.s3_service import S3Service

logger = logging.getLogger(__name__)

class VLMService:
    """Vision Language Model service for processing question paper images"""
    
    def __init__(self):
        """Initialize VLM service with configuration"""
        self.config = Config()
        
        # Initialize S3 service
        self.s3_service = S3Service()
        
        # Set S3 configuration
        self.question_paper_prefix = 'question-paper/'
        
        # Initialize OpenAI client
        self.openai_api_key = Config.OPENAI_API_KEY
        
        try:
            if self.openai_api_key:
                self.openai_client = OpenAI(api_key=self.openai_api_key)
                logger.info("OpenAI client initialized successfully")
            else:
                self.openai_client = None
                logger.warning("OpenAI API key not configured")
        except Exception as e:
            logger.error(f"OpenAI client initialization failed: {e}")
            self.openai_client = None
        
        # Configure supported image formats
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp'}
        
        # VLM processing parameters
        self.vlm_model = Config.OPENAI_VLM_MODEL
        self.max_tokens = Config.OPENAI_MAX_TOKENS
        self.temperature = Config.OPENAI_TEMPERATURE
        
        logger.info(f"VLM service initialized with S3 bucket: {Config.S3_BUCKET}")
    
    def check_health(self) -> Dict[str, any]:
        """Check health of VLM service and dependencies"""
        try:
            # Check S3 service
            s3_status = self.s3_service.test_connection() if self.s3_service.is_configured() else False
            s3_configured = self.s3_service.is_configured()
            
            # Check Django API connectivity
            django_status = False
            try:
                django_health = requests.get(
                    f'{Config.DJANGO_API_BASE_URL}/status/', 
                    timeout=Config.HEALTH_CHECK_TIMEOUT
                )
                django_status = django_health.status_code == 200
            except Exception as e:
                logger.warning(f"Django API health check failed: {e}")
            
            # Check OpenAI API
            openai_configured = bool(self.openai_client and self.openai_api_key)
            
            # Test OpenAI API if configured
            openai_status = False
            if openai_configured:
                try:
                    # Simple API test
                    test_response = self.openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": "test"}],
                        max_tokens=1
                    )
                    openai_status = True
                except Exception as e:
                    logger.warning(f"OpenAI API test failed: {e}")
            
            # Overall health status
            overall_success = s3_configured and s3_status and openai_configured and openai_status
            
            return {
                'success': overall_success,
                'details': {
                    's3_configured': s3_configured,
                    's3_connected': s3_status,
                    's3_bucket': Config.S3_BUCKET,
                    's3_prefix': self.question_paper_prefix,
                    'openai_configured': openai_configured,
                    'openai_connected': openai_status,
                    'openai_model': self.vlm_model,
                    'django_api_status': 'connected' if django_status else 'disconnected',
                    'django_api_url': Config.DJANGO_API_BASE_URL,
                    'supported_formats': list(self.supported_formats),
                    'max_tokens': self.max_tokens,
                    'temperature': self.temperature
                }
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'success': False,
                'details': {
                    'error': str(e),
                    's3_configured': False,
                    's3_connected': False,
                    'openai_configured': False,
                    'openai_connected': False,
                    'django_api_status': 'error'
                }
            }
    
    def get_image_keys_from_s3(self, uuid: str) -> List[str]:
        """Get all image keys from S3 for a given UUID"""
        if not self.s3_service.is_configured():
            raise Exception("S3 service not configured")
            
        prefix = f"{self.question_paper_prefix}{uuid}/"
        image_keys = []
        
        logger.info(f"Searching S3 with prefix: {prefix}")
        
        try:
            # Use S3 service to list objects
            objects = self.s3_service.list_objects(prefix)
            
            total_objects = len(objects)
            logger.info(f"Found {total_objects} objects in S3")
            
            for obj in objects:
                # Handle both string keys and object dictionaries
                if isinstance(obj, dict):
                    # If it's a dictionary, extract the key
                    obj_key = obj.get('Key') or obj.get('key') or obj.get('name', '')
                else:
                    # If it's a string, use it directly
                    obj_key = str(obj)
                
                logger.debug(f"Found S3 object: {obj_key}")
                
                if self._is_image_file(obj_key):
                    image_keys.append(obj_key)
                    logger.debug(f"Added image key: {obj_key}")
            
            logger.info(f"Total image files found: {len(image_keys)}")
            
            # Sort to maintain page order
            image_keys.sort()
            return image_keys
            
        except Exception as e:
            logger.error(f"Error listing S3 objects: {e}")
            raise Exception(f"Failed to list images from S3: {str(e)}")
    
    def download_image_from_s3(self, key: str) -> bytes:
        """Download image bytes from S3"""
        if not self.s3_service.is_configured():
            raise Exception("S3 service not configured")
            
        try:
            return self.s3_service.download_file(key)
        except Exception as e:
            logger.error(f"Error downloading image {key}: {e}")
            raise Exception(f"Failed to download image: {str(e)}")
    
    def process_image_with_vlm(self, image_bytes: bytes) -> Dict[str, any]:
        """Process image with OpenAI GPT-4 Vision - Focus on diagrams and equations only"""
        if not self.openai_client:
            return {
                'diagram_number': None,
                'description': 'OpenAI client not configured',
                'status': 'error'
            }
            
        try:
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            # VLM prompt specifically for diagram and equation extraction
            vlm_prompt = """Analyze this image and extract ONLY:
1. Any diagram, figure, or chart numbers (e.g., "Diagram 1", "Figure 2", "Chart 3")
2. Mathematical equations or formulas present
3. Brief description of diagrams, charts, graphs, or visual elements

IGNORE: Regular text, paragraphs, questions, or written content.
FOCUS ON: Diagrams, equations, figures, graphs, visual content only.

Return ONLY a JSON object with this exact format:
{
    "diagram_number": <number or null>,
    "description": "<description of diagrams/equations only>"
}"""
            
            response = self.openai_client.chat.completions.create(
                model=self.vlm_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": vlm_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            # Parse the JSON response
            response_text = response.choices[0].message.content.strip()
            logger.debug(f"VLM raw response: {response_text}")
            
            # Clean up response if it contains markdown formatting
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '').strip()
            
            try:
                result = json.loads(response_text)
                return {
                    'diagram_number': result.get('diagram_number'),
                    'description': result.get('description', 'No description available'),
                    'status': 'success'
                }
            except json.JSONDecodeError as json_error:
                logger.warning(f"JSON decode error: {json_error}, attempting fallback parsing")
                # Fallback parsing if JSON is malformed
                diagram_number = self._extract_diagram_number_fallback(response_text)
                return {
                    'diagram_number': diagram_number,
                    'description': response_text,
                    'status': 'partial'
                }
            
        except Exception as e:
            logger.error(f"OpenAI VLM processing error: {e}")
            return {
                'diagram_number': None,
                'description': f"VLM processing failed: {str(e)}",
                'status': 'error'
            }
    
    def _extract_diagram_number_fallback(self, text: str) -> Optional[int]:
        """Fallback method to extract diagram number using regex"""
        patterns = [
            r'(?:diagram|figure|chart|table)\s*(\d+)',
            r'(\d+)\s*(?:diagram|figure|chart|table)',
            r'diagram_number["\']?\s*:\s*(\d+)',
            r'"diagram_number"\s*:\s*(\d+)',
            r'diagram\s*#?\s*(\d+)',
            r'fig\w*\s*(\d+)',
            r'chart\s*(\d+)'
        ]
        
        text_lower = text.lower()
        for pattern in patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def _is_image_file(self, filename: str) -> bool:
        """Check if file is a supported image format"""
        _, ext = os.path.splitext(filename.lower())
        return ext in self.supported_formats
    
    def send_vlm_data_to_django(self, question_paper_uuid: str, vlm_data: dict) -> Dict[str, any]:
        """Send VLM data to Django API using the same endpoint as OCR"""
        try:
            payload = {
                "question_paper_uuid": str(question_paper_uuid),
                "vlm_json": vlm_data  # This will be saved to the vlm_json field
            }
            
            headers = {
                'Content-Type': 'application/json',
            }
            
            logger.info(f"Sending VLM data to Django API for UUID: {question_paper_uuid}")
            
            response = requests.post(
                Config.DJANGO_PROCESS_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=Config.DJANGO_API_TIMEOUT
            )
            
            logger.info(f"Django API response status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                return {
                    'success': True,
                    'response': response.json(),
                    'status_code': response.status_code
                }
            else:
                logger.error(f"Django API error response: {response.text}")
                return {
                    'success': False,
                    'error': f'Django API returned {response.status_code}',
                    'response': response.text
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Django API request failed: {e}")
            return {
                'success': False,
                'error': f'Failed to connect to Django API: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Error sending data to Django: {e}")
            return {
                'success': False,
                'error': f'Error sending data to Django: {str(e)}'
            }
    
    def process_images_with_database_save(self, uuid: str) -> Dict[str, any]:
        """Process all images for a given UUID and save to database"""
        try:
            logger.info(f"Starting VLM processing with database save for UUID: {uuid}")
            
            # Get image keys from S3
            image_keys = self.get_image_keys_from_s3(uuid)
            
            if not image_keys:
                return {
                    'success': False,
                    'error': f'No images found for UUID: {uuid}',
                    'details': {'searched_prefix': f'{self.question_paper_prefix}{uuid}/'}
                }
            
            logger.info(f"Found {len(image_keys)} images to process")
            
            # Process each image
            all_pages_data = []
            page_number = 1
            successful_pages = 0
            
            for image_key in image_keys:
                try:
                    logger.info(f"Processing image {page_number}/{len(image_keys)}: {image_key}")
                    
                    # Download image
                    image_bytes = self.download_image_from_s3(image_key)
                    logger.debug(f"Downloaded image bytes: {len(image_bytes)}")
                    
                    # Process with VLM
                    vlm_result = self.process_image_with_vlm(image_bytes)
                    
                    # Create result entry
                    page_data = {
                        'page_number': page_number,
                        'diagram_number': vlm_result['diagram_number'],
                        'description': vlm_result['description'],
                        'image_path': image_key,
                        'processing_status': vlm_result['status']
                    }
                    
                    all_pages_data.append(page_data)
                    
                    if vlm_result['status'] in ['success', 'partial']:
                        successful_pages += 1
                    
                    logger.info(f"Completed processing page {page_number}: {vlm_result['status']}")
                    
                except Exception as e:
                    logger.error(f"Error processing image {image_key}: {e}")
                    # Add error entry for this page
                    error_data = {
                        'page_number': page_number,
                        'diagram_number': None,
                        'description': f"Error processing image: {str(e)}",
                        'image_path': image_key,
                        'processing_status': 'error'
                    }
                    all_pages_data.append(error_data)
                
                page_number += 1
            
            # Prepare VLM data structure for Django
            vlm_json_data = {
                'question_paper_uuid': str(uuid),
                'total_pages': len(image_keys),
                'processed_pages': successful_pages,
                'processing_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                's3_source': f's3://{Config.S3_BUCKET}/{self.question_paper_prefix}{uuid}/',
                'vlm_model': self.vlm_model,
                'pages_data': all_pages_data,
                'processing_summary': {
                    'successful_pages': len([p for p in all_pages_data if p['processing_status'] == 'success']),
                    'partial_pages': len([p for p in all_pages_data if p['processing_status'] == 'partial']),
                    'failed_pages': len([p for p in all_pages_data if p['processing_status'] == 'error']),
                    'total_diagrams_found': len([p for p in all_pages_data if p.get('diagram_number') is not None]),
                    'service_type': f'VLM_{self.vlm_model}',
                    'service_version': '1.0.0'
                }
            }
            
            logger.info(f"VLM processing completed. Summary: {vlm_json_data['processing_summary']}")
            
            # Send data to Django API
            django_result = self.send_vlm_data_to_django(uuid, vlm_json_data)
            
            if not django_result['success']:
                logger.error(f"Failed to save to Django: {django_result['error']}")
                return {
                    'success': False,
                    'error': 'VLM processing completed but failed to store in database',
                    'details': {
                        'django_error': django_result['error'],
                        'vlm_data': vlm_json_data  # Return VLM data for debugging
                    }
                }
            
            logger.info("VLM processing and database save completed successfully")
            
            # Return successful response
            return {
                'success': True,
                'data': {
                    'total_pages': len(all_pages_data),
                    'processing_summary': vlm_json_data['processing_summary'],
                    'django_response': django_result['response'],
                    'pages_data': all_pages_data
                }
            }
            
        except Exception as e:
            logger.error(f"Error in process_images_with_database_save: {e}")
            return {
                'success': False,
                'error': str(e),
                'details': {'uuid': uuid, 'service': 'VLM'}
            }
    
    def process_images_only(self, uuid: str) -> Dict[str, any]:
        """Process all images for a given UUID without saving to database"""
        try:
            logger.info(f"Starting VLM processing (no database save) for UUID: {uuid}")
            
            # Get image keys from S3
            image_keys = self.get_image_keys_from_s3(uuid)
            
            if not image_keys:
                return {
                    'success': False,
                    'error': f'No images found for UUID: {uuid}',
                    'details': {'searched_prefix': f'{self.question_paper_prefix}{uuid}/'}
                }
            
            logger.info(f"Found {len(image_keys)} images to process")
            
            # Process each image
            results = []
            page_number = 1
            
            for image_key in image_keys:
                try:
                    logger.info(f"Processing image {page_number}/{len(image_keys)}: {image_key}")
                    
                    # Download image
                    image_bytes = self.download_image_from_s3(image_key)
                    
                    # Process with VLM
                    vlm_result = self.process_image_with_vlm(image_bytes)
                    
                    # Create result entry
                    page_result = {
                        'page_number': page_number,
                        'diagram_number': vlm_result['diagram_number'],
                        'description': vlm_result['description'],
                        'image_path': image_key,
                        'processing_status': vlm_result['status']
                    }
                    
                    results.append(page_result)
                    logger.info(f"Completed processing page {page_number}: {vlm_result['status']}")
                    
                except Exception as e:
                    logger.error(f"Error processing image {image_key}: {e}")
                    # Add error entry for this page
                    error_result = {
                        'page_number': page_number,
                        'diagram_number': None,
                        'description': f"Error processing image: {str(e)}",
                        'image_path': image_key,
                        'processing_status': 'error'
                    }
                    results.append(error_result)
                
                page_number += 1
            
            logger.info("VLM processing (no database save) completed successfully")
            
            # Return successful response
            return {
                'success': True,
                'data': {
                    'total_pages': len(results),
                    'pages_data': results
                }
            }
            
        except Exception as e:
            logger.error(f"Error in process_images_only: {e}")
            return {
                'success': False,
                'error': str(e),
                'details': {'uuid': uuid, 'service': 'VLM'}
            }
    
    def debug_s3_structure(self, uuid: str) -> Dict[str, any]:
        """Debug endpoint to see what's actually in S3"""
        if not self.s3_service.is_configured():
            raise Exception("S3 service not configured")
            
        # Search broadly for the UUID
        prefixes_to_check = [
            f"question-paper/{uuid}/",
            f"question paper/{uuid}/", 
            f"{uuid}/",
            f"question_paper/{uuid}/",
            f"questionpaper/{uuid}/",
            f"qp/{uuid}/",
            f"images/{uuid}/"
        ]
        
        results = {}
        
        for prefix in prefixes_to_check:
            logger.info(f"Checking S3 prefix: {prefix}")
            try:
                objects = self.s3_service.list_objects(prefix)
                results[prefix] = objects
                logger.info(f"Found {len(objects)} objects in prefix: {prefix}")
                
            except Exception as e:
                logger.warning(f"Error checking prefix {prefix}: {e}")
                results[prefix] = f"Error: {str(e)}"
        
        return results
    
    def get_service_info(self) -> Dict[str, any]:
        """Get detailed service information"""
        health_check = self.check_health()
        
        return {
            'service_name': 'VLM Image Processor',
            'service_version': '1.0.0',
            'description': 'Vision Language Model service for extracting diagrams and equations from question paper images',
            'model': self.vlm_model,
            'configuration': {
                'max_tokens': self.max_tokens,
                'temperature': self.temperature,
                'supported_formats': list(self.supported_formats),
                's3_bucket': Config.S3_BUCKET,
                's3_prefix': self.question_paper_prefix
            },
            'health_status': health_check,
            'capabilities': [
                'Diagram number extraction',
                'Mathematical equation detection',
                'Figure and chart identification',
                'Visual element description',
                'S3 image processing',
                'Django database integration'
            ]
        }