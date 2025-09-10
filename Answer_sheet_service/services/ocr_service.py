import requests
import time
import io
from datetime import datetime
from PIL import Image
from config import Config
from services.s3_service import S3Service

class OCRService:
    def __init__(self):
        self.subscription_key = Config.AZURE_SUBSCRIPTION_KEY
        self.endpoint = Config.AZURE_ENDPOINT
        self.read_url = self.endpoint + "vision/v3.2/read/analyze"
        self.s3_service = S3Service()
        
        print(f"OCR Service initialized - Endpoint: {self.endpoint}")
        print(f"Azure OCR dimension limits: {Config.MIN_DIMENSION}x{Config.MIN_DIMENSION} to {Config.MAX_DIMENSION}x{Config.MAX_DIMENSION}")
    
    def resize_image_for_ocr(self, image_data):
        """
        Resize and optimize image to fit Azure OCR requirements:
        - Dimensions: 50x50 to 10000x10000 pixels
        - File size: <= 4MB
        """
        try:
            # Open image from bytes
            image = Image.open(io.BytesIO(image_data))
            original_width, original_height = image.size
            original_size = len(image_data)
            
            print(f"Original image - Dimensions: {original_width}x{original_height}, Size: {original_size / (1024*1024):.2f}MB")
            
            # Start with original dimensions
            new_width, new_height = original_width, original_height
            resized = False
            
            # Step 1: Fix dimensions if needed
            if original_width < Config.MIN_DIMENSION or original_height < Config.MIN_DIMENSION:
                scale_factor = max(Config.MIN_DIMENSION / original_width, Config.MIN_DIMENSION / original_height)
                new_width = int(original_width * scale_factor)
                new_height = int(original_height * scale_factor)
                resized = True
                print(f"Scaling up image by factor {scale_factor:.2f}")
            elif original_width > Config.MAX_DIMENSION or original_height > Config.MAX_DIMENSION:
                scale_factor = min(Config.MAX_DIMENSION / original_width, Config.MAX_DIMENSION / original_height)
                new_width = int(original_width * scale_factor)
                new_height = int(original_height * scale_factor)
                resized = True
                print(f"Scaling down image by factor {scale_factor:.2f}")
            
            # Step 2: Process image and optimize file size
            if resized or original_size > Config.MAX_FILE_SIZE:
                # Resize image if dimensions changed
                if resized:
                    processed_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    print(f"Resized image dimensions: {new_width}x{new_height}")
                else:
                    processed_image = image
                
                # Convert to RGB if needed (for JPEG compatibility)
                if processed_image.mode in ('RGBA', 'LA', 'P'):
                    rgb_image = Image.new('RGB', processed_image.size, (255, 255, 255))
                    if processed_image.mode == 'P':
                        processed_image = processed_image.convert('RGBA')
                    rgb_image.paste(processed_image, mask=processed_image.split()[-1] if processed_image.mode in ('RGBA', 'LA') else None)
                    processed_image = rgb_image
                
                # Try different quality levels to get under 4MB
                for quality in [95, 85, 75, 65, 55, 45, 35]:
                    output = io.BytesIO()
                    processed_image.save(output, format='JPEG', quality=quality, optimize=True)
                    processed_data = output.getvalue()
                    processed_size = len(processed_data)
                    
                    print(f"Quality {quality}: {processed_size / (1024*1024):.2f}MB")
                    
                    if processed_size <= Config.MAX_FILE_SIZE:
                        print(f"Final image - Dimensions: {new_width}x{new_height}, Size: {processed_size / (1024*1024):.2f}MB, Quality: {quality}")
                        return processed_data, new_width, new_height, True
                
                # If still too large, reduce dimensions further
                print("Still too large after quality reduction, reducing dimensions...")
                reduction_factor = 0.9
                attempts = 0
                max_attempts = 10
                
                while processed_size > Config.MAX_FILE_SIZE and attempts < max_attempts:
                    new_width = int(new_width * reduction_factor)
                    new_height = int(new_height * reduction_factor)
                    
                    # Check if dimensions are still valid
                    if new_width < Config.MIN_DIMENSION or new_height < Config.MIN_DIMENSION:
                        print("Cannot reduce dimensions further without going below minimum")
                        break
                    
                    processed_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # Convert to RGB if needed
                    if processed_image.mode in ('RGBA', 'LA', 'P'):
                        rgb_image = Image.new('RGB', processed_image.size, (255, 255, 255))
                        if processed_image.mode == 'P':
                            processed_image = processed_image.convert('RGBA')
                        rgb_image.paste(processed_image, mask=processed_image.split()[-1] if processed_image.mode in ('RGBA', 'LA') else None)
                        processed_image = rgb_image
                    
                    output = io.BytesIO()
                    processed_image.save(output, format='JPEG', quality=75, optimize=True)
                    processed_data = output.getvalue()
                    processed_size = len(processed_data)
                    
                    attempts += 1
                    print(f"Attempt {attempts}: {new_width}x{new_height}, {processed_size / (1024*1024):.2f}MB")
                
                if processed_size <= Config.MAX_FILE_SIZE:
                    print(f"Final optimized image - Dimensions: {new_width}x{new_height}, Size: {processed_size / (1024*1024):.2f}MB")
                    return processed_data, new_width, new_height, True
                else:
                    raise Exception(f"Unable to reduce image size below 4MB limit. Final size: {processed_size / (1024*1024):.2f}MB")
            
            # No processing needed
            print("Image already within acceptable limits")
            return image_data, original_width, original_height, False
            
        except Exception as e:
            print(f"Error processing image: {e}")
            raise Exception(f"Image processing failed: {str(e)}")
    
    def download_image(self, image_url):
        """Download image from URL (S3 or HTTP)"""
        image_data = None
        s3_error = None
        
        if 's3.amazonaws.com' in image_url:
            print("Detected S3 URL, attempting S3 download...")
            image_data, s3_error = self.s3_service.download_file(image_url)
            
            if image_data is None:
                print(f"S3 download failed: {s3_error}")
                print("Falling back to direct HTTP request...")
                # Fall back to direct HTTP request
                image_response = requests.get(image_url, timeout=30)
                if image_response.status_code != 200:
                    return None, f'Failed to download image from URL: {image_url}. S3 Error: {s3_error}. HTTP Status: {image_response.status_code}'
                image_data = image_response.content
            else:
                print("Successfully downloaded from S3")
        else:
            # Regular HTTP download
            print("Regular HTTP download...")
            image_response = requests.get(image_url, timeout=30)
            if image_response.status_code != 200:
                return None, f'Failed to download image from URL: {image_url}. Status: {image_response.status_code}'
            image_data = image_response.content
        
        return image_data, None
    
    def poll_result(self, op_url, headers, max_retries=10, retry_delay=1):
        """Poll Azure OCR result"""
        for attempt in range(max_retries):
            response = requests.get(op_url, headers=headers)

            if response.status_code == 429:
                wait_time = retry_delay * (2 ** attempt)
                print(f"Rate limited (429). Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue

            try:
                result = response.json()
            except Exception as e:
                raise Exception(f"Failed to parse OCR response JSON: {e}")

            status = result.get("status")
            if status in ["succeeded", "failed"]:
                return result

            time.sleep(1)

        raise Exception("Azure OCR polling timed out or failed after multiple retries.")
    
    def convert_bbox_format(self, bounding_box):
        """Convert bounding box format"""
        x_coords = bounding_box[::2]
        y_coords = bounding_box[1::2]
        x0, y0 = min(x_coords), min(y_coords)
        x1, y1 = max(x_coords), max(y_coords)
        return [x0, y0, x1, y1]
    
    def extract_text_from_url(self, image_url, word_level=False):
        """Extract text from an image URL using Azure OCR with automatic resizing"""
        try:
            print(f"Processing image from: {image_url}")
            
            # Download image data
            image_data, error = self.download_image(image_url)
            if image_data is None:
                return {'success': False, 'error': error}
            
            # Resize image if necessary
            try:
                processed_image_data, width, height, was_resized = self.resize_image_for_ocr(image_data)
                resize_info = {
                    'original_size_bytes': len(image_data),
                    'processed_size_bytes': len(processed_image_data),
                    'dimensions': f"{width}x{height}",
                    'was_resized': was_resized
                }
            except Exception as resize_error:
                return {
                    'success': False,
                    'error': f'Image preprocessing failed: {str(resize_error)}',
                    'resize_error': str(resize_error)
                }
            
            headers = {
                "Ocp-Apim-Subscription-Key": self.subscription_key,
                "Content-Type": "application/octet-stream"
            }

            # Add retry logic for the initial POST request
            max_retries = 10
            retry_delay = 1
            
            for attempt in range(max_retries):
                response = requests.post(self.read_url, headers=headers, data=processed_image_data)
                
                if response.status_code == 429:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"Rate limited (429) on initial request. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                elif response.status_code == 202:
                    break
                else:
                    return {
                        'success': False,
                        'error': 'Azure OCR failed',
                        'details': response.text,
                        'status_code': response.status_code,
                        'resize_info': resize_info
                    }
            else:
                return {
                    'success': False,
                    'error': 'Azure OCR failed after multiple retries',
                    'details': 'Rate limit exceeded',
                    'resize_info': resize_info
                }

            operation_url = response.headers["Operation-Location"]
            result = self.poll_result(operation_url, headers)

            if result["status"] != "succeeded":
                return {
                    'success': False,
                    'error': 'OCR analysis failed',
                    'result_status': result.get("status"),
                    'resize_info': resize_info
                }

            output = []

            for page_result in result["analyzeResult"]["readResults"]:
                for line in page_result["lines"]:
                    if word_level:
                        line_text = line["text"]
                        if "words" in line:
                            for idx, word in enumerate(line["words"]):
                                output.append({
                                    "id": idx,
                                    "text": word["text"],
                                    "boundingBox": self.convert_bbox_format(word["boundingBox"]),
                                    "confidence": word.get("confidence", None),
                                    "line_text": line_text
                                })
                    else:
                        line_obj = {
                            "text": line["text"],
                            "boundingBox": self.convert_bbox_format(line["boundingBox"]),
                            "confidence": None
                        }
                        if "words" in line:
                            confidences = [word.get("confidence", 0) for word in line["words"] if "confidence" in word]
                            if confidences:
                                line_obj["confidence"] = sum(confidences) / len(confidences)
                        output.append(line_obj)

            return {
                "success": True, 
                "extracted_text": output,
                "resize_info": resize_info
            }
            
        except requests.RequestException as e:
            return {'success': False, 'error': f'Network error downloading image: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'OCR processing failed: {str(e)}'}
    
    def get_image_urls_from_django(self, roll_no, question_paper_uuid):
        """Fetch image URLs from Django API"""
        try:
            url = f"{Config.DJANGO_API_BASE}/roll/{roll_no}/uuid/{question_paper_uuid}/images/"
            print(f"Making request to Django API: {url}")
            
            response = requests.get(url, timeout=30)
            print(f"Django API response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"Django API response data: {data}")
                    if data.get('success'):
                        return {
                            'success': True,
                            'image_urls': data.get('image_urls', []),
                            'roll_no': data.get('roll_no'),
                            'question_paper_uuid': data.get('question_paper_uuid'),
                            'image_count': data.get('image_count', 0)
                        }
                    else:
                        return {'success': False, 'error': data.get('error', 'Unknown error from Django API')}
                except ValueError as e:
                    print(f"Failed to parse JSON response: {e}")
                    print(f"Raw response: {response.text}")
                    return {'success': False, 'error': f'Invalid JSON response from Django API: {response.text}'}
            elif response.status_code == 404:
                print(f"Django API 404 response: {response.text}")
                return {'success': False, 'error': f'Answer script not found for roll_no: {roll_no}, UUID: {question_paper_uuid}', 'status_code': 404}
            else:
                print(f"Django API error response: {response.text}")
                return {'success': False, 'error': f'Django API returned status code: {response.status_code}', 'response_text': response.text}
                
        except requests.RequestException as e:
            return {'success': False, 'error': f'Failed to connect to Django API: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'Error fetching image URLs: {str(e)}'}
    
    def send_webhook_notification(self, data):
        """Send OCR results to webhook URL"""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'OCR-API/1.0'
        }
        
        for attempt in range(Config.WEBHOOK_MAX_RETRIES):
            try:
                print(f"Sending webhook notification (attempt {attempt + 1}/{Config.WEBHOOK_MAX_RETRIES})")
                
                response = requests.post(
                    Config.WEBHOOK_URL, 
                    json=data, 
                    headers=headers,
                    timeout=Config.WEBHOOK_TIMEOUT
                )
                
                print(f"Webhook response status: {response.status_code}")
                
                if response.status_code in [200, 201, 202]:
                    print("Webhook notification sent successfully")
                    return True
                else:
                    print(f"Webhook returned non-success status: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                print(f"Webhook timeout on attempt {attempt + 1}")
            except requests.exceptions.ConnectionError as e:
                print(f"Webhook connection error on attempt {attempt + 1}: {str(e)}")
            except requests.exceptions.RequestException as e:
                print(f"Webhook request error on attempt {attempt + 1}: {str(e)}")
            except Exception as e:
                print(f"Unexpected webhook error on attempt {attempt + 1}: {str(e)}")
            
            if attempt < Config.WEBHOOK_MAX_RETRIES - 1:
                print(f"Retrying webhook in 2 seconds...")
                time.sleep(2)
        
        print("Failed to send webhook notification after all retries")
        return False
    
    def process_answer_sheet_ocr(self, roll_no, question_paper_uuid, word_level=False, process_all=True, image_indices=[]):
        """Process OCR for answer sheet images"""
        try:
            print(f"Processing OCR for roll_no: {roll_no}, UUID: {question_paper_uuid}")
            
            # Fetch image URLs from Django API
            django_response = self.get_image_urls_from_django(roll_no, question_paper_uuid)
            
            if not django_response['success']:
                return {
                    'success': False,
                    'error': f"Failed to fetch image URLs: {django_response['error']}"
                }

            image_urls = django_response['image_urls']
            
            if not image_urls:
                return {
                    'success': False,
                    'error': 'No images found for the given roll number and UUID'
                }

            # Determine which images to process
            if not process_all and image_indices:
                # Validate indices
                valid_indices = [i for i in image_indices if 0 <= i < len(image_urls)]
                if not valid_indices:
                    return {
                        'success': False,
                        'error': f'No valid image indices. Available indices: 0-{len(image_urls)-1}'
                    }
                
                images_to_process = [(i, image_urls[i]) for i in valid_indices]
            else:
                images_to_process = list(enumerate(image_urls))

            # Process OCR for each image
            ocr_results = []
            total_images = len(images_to_process)
            processed_count = 0
            error_count = 0
            resized_count = 0

            for index, image_url in images_to_process:
                print(f"Processing image {index + 1}/{total_images}: {image_url}")
                
                ocr_result = self.extract_text_from_url(image_url, word_level=word_level)
                
                result_entry = {
                    'image_index': index,
                    'image_url': image_url,
                    'ocr_result': ocr_result
                }
                
                if ocr_result.get('success'):
                    processed_count += 1
                    result_entry['status'] = 'success'
                    result_entry['text_lines_count'] = len(ocr_result.get('extracted_text', []))
                    
                    # Track resizing info
                    resize_info = ocr_result.get('resize_info', {})
                    if resize_info.get('was_resized'):
                        resized_count += 1
                        result_entry['resized'] = True
                        result_entry['resize_info'] = resize_info
                    
                else:
                    error_count += 1
                    result_entry['status'] = 'failed'
                    result_entry['error'] = ocr_result.get('error', 'Unknown OCR error')
                    
                    # Include resize info even for failed cases
                    if 'resize_info' in ocr_result:
                        result_entry['resize_info'] = ocr_result['resize_info']

                ocr_results.append(result_entry)

            # Prepare response
            response_data = {
                'success': True,
                'roll_no': roll_no,
                'question_paper_uuid': question_paper_uuid,
                'processing_summary': {
                    'total_images_available': len(image_urls),
                    'images_processed': total_images,
                    'successful_ocr': processed_count,
                    'failed_ocr': error_count,
                    'images_resized': resized_count,
                    'word_level': word_level,
                    's3_available': self.s3_service.is_configured(),
                    'status': 'completed',
                    'timestamp': datetime.now().isoformat()
                },
                'ocr_results': ocr_results,
                'timestamp': datetime.now().isoformat()
            }

            # Send webhook notification
            print("Sending webhook notification...")
            webhook_success = self.send_webhook_notification(response_data)
            
            if webhook_success:
                print("Webhook notification sent successfully")
                response_data['webhook_status'] = 'sent'
            else:
                print("Failed to send webhook notification")
                response_data['webhook_status'] = 'failed'

            return response_data

        except Exception as e:
            print(f"Unexpected error in OCR processing: {str(e)}")
            
            return {
                'success': False,
                'error': f'OCR processing failed: {str(e)}',
                'roll_no': roll_no,
                'question_paper_uuid': question_paper_uuid,
                'timestamp': datetime.now().isoformat()
            }