import requests
import json
import time
import logging
from datetime import datetime
import re

from config import Config

logger = logging.getLogger(__name__)

class SchedulerService:
    """Service class for handling rubric generation and processing"""
    
    def __init__(self):
        """Initialize the scheduler service with configuration"""
        self.django_api_base_url = Config.DJANGO_API_BASE_URL
        self.rubric_generation_api_url = Config.RUBRIC_GENERATION_API_URL
        self.process_rubric_api_url = Config.PROCESS_RUBRIC_API_URL
        self.request_timeout = Config.DJANGO_API_TIMEOUT

    def parse_json_from_response(self, response_text):
        """Extract and parse JSON from response that might be wrapped in markdown code blocks"""
        try:
            # First, try to parse directly as JSON
            return json.loads(response_text)
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract JSON from markdown code blocks
            # Look for ```json ... ``` or ``` ... ``` blocks
            json_pattern = r'```(?:json)?\s*([\s\S]*?)```'
            matches = re.findall(json_pattern, response_text, re.MULTILINE)
            
            for match in matches:
                try:
                    # Clean up the match and try to parse as JSON
                    cleaned_match = match.strip()
                    return json.loads(cleaned_match)
                except json.JSONDecodeError:
                    continue
            
            # If no valid JSON found in code blocks, raise an error
            raise ValueError("No valid JSON found in response")

    def fetch_qp_data_from_django(self, question_paper_uuid):
        """Fetch QP data from Django API by UUID"""
        try:
            url = f'{self.django_api_base_url}/uuid/{question_paper_uuid}/'
            
            headers = {
                'Content-Type': 'application/json',
            }
            
            logger.info(f"Fetching QP data - URL: {url}")
            logger.info(f"Request headers: {headers}")
            
            response = requests.get(url, headers=headers, timeout=self.request_timeout)
            
            logger.info(f"Django API response status: {response.status_code}")
            logger.info(f"Django API response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                response_data = response.json()
                logger.info(f"Django API response data keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'Not a dict'}")
                if isinstance(response_data, dict) and 'data' in response_data:
                    qp_data = response_data['data']
                    logger.info(f"QP data keys: {list(qp_data.keys()) if isinstance(qp_data, dict) else 'Not a dict'}")
                    if isinstance(qp_data, dict):
                        logger.info(f"OCR data available: {'ocr_json' in qp_data}")
                        logger.info(f"VLM data available: {'vlm_json' in qp_data}")
            else:
                logger.error(f"Django API error response: {response.text}")
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'data': response.json()
                }
            elif response.status_code == 404:
                return {
                    'success': False,
                    'error': 'Question paper not found with the provided UUID'
                }
            else:
                return {
                    'success': False,
                    'error': f'Django API returned {response.status_code}',
                    'response': response.text
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception while fetching QP data: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to connect to Django API: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Exception while fetching QP data: {str(e)}")
            return {
                'success': False,
                'error': f'Error fetching data from Django: {str(e)}'
            }

    def call_rubric_generation_api(self, question_paper_text, vlm_description):
        """Call the rubric generation API and parse JSON response"""
        try:
            payload = {
                'question_paper_text': question_paper_text,
                'vlm_description': vlm_description
            }
            
            headers = {
                'Content-Type': 'application/json',
            }
            
            logger.info(f"Calling rubric generation API - URL: {self.rubric_generation_api_url}")
            logger.info(f"Request headers: {headers}")
            logger.info(f"Payload keys: {list(payload.keys())}")
            logger.info(f"Question paper text length: {len(question_paper_text)}")
            logger.info(f"Question paper text preview: {question_paper_text[:200]}...")
            logger.info(f"VLM description length: {len(vlm_description)}")
            logger.info(f"VLM description preview: {vlm_description[:200]}...")
            
            response = requests.post(
                self.rubric_generation_api_url,
                json=payload,
                headers=headers,
                timeout=300  # 5 minutes timeout for rubric generation
            )
            
            logger.info(f"Rubric API response status: {response.status_code}")
            logger.info(f"Rubric API response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                api_response = response.json()
                logger.info(f"Rubric API response keys: {list(api_response.keys()) if isinstance(api_response, dict) else 'Not a dict'}")
                
                # Parse the rubric result if it contains JSON strings
                if 'result' in api_response and isinstance(api_response['result'], str):
                    logger.info(f"Raw rubric result (first 300 chars): {api_response['result'][:300]}...")
                    try:
                        # Parse the JSON string in the result field
                        parsed_rubric = self.parse_json_from_response(api_response['result'])
                        logger.info(f"Successfully parsed rubric JSON, type: {type(parsed_rubric)}")
                        if isinstance(parsed_rubric, list):
                            logger.info(f"Parsed rubric contains {len(parsed_rubric)} items")
                        api_response['result'] = parsed_rubric
                    except (ValueError, json.JSONDecodeError) as e:
                        logger.warning(f"Could not parse rubric JSON: {e}")
                        # Keep the original string if parsing fails
                        pass
            else:
                logger.error(f"Rubric API error response: {response.text}")
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'result': api_response
                }
            else:
                return {
                    'success': False,
                    'error': f'Rubric API returned {response.status_code}',
                    'response': response.text
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception while calling rubric API: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to connect to Rubric API: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Exception while calling rubric API: {str(e)}")
            return {
                'success': False,
                'error': f'Error calling Rubric API: {str(e)}'
            }

    def extract_vlm_description_from_data(self, qp_data):
        """Extract VLM description from the vlm_json field in the database and format as 'Page X: ...'"""
        try:
            # Check if vlm_json field exists and has content
            if 'vlm_json' not in qp_data:
                logger.warning("vlm_json field not found in database")
                return "No vlm_json field found in database."
            
            if not qp_data['vlm_json']:
                logger.warning("vlm_json field is empty in database")
                return "vlm_json field is empty in database."
            
            vlm_data = qp_data['vlm_json']
            logger.info(f"Found vlm_json data, type: {type(vlm_data)}")
            
            # If vlm_data is a string, try to parse it as JSON
            if isinstance(vlm_data, str):
                try:
                    vlm_data = json.loads(vlm_data)
                    logger.info("Successfully parsed vlm_json as JSON")
                except json.JSONDecodeError:
                    logger.info("vlm_json is a plain string, using as-is")
                    return vlm_data
            
            # Extract descriptions from pages_data
            if isinstance(vlm_data, dict) and 'pages_data' in vlm_data:
                pages_data = vlm_data['pages_data']
                logger.info(f"Found pages_data with {len(pages_data)} pages")
                
                descriptions = []
                for page in pages_data:
                    if isinstance(page, dict) and 'description' in page and page['description']:
                        page_num = page.get('page_number', len(descriptions) + 1)
                        description = page['description'].strip()
                        
                        # Skip pages with no meaningful visual content
                        if description.lower() not in [
                            'no diagrams, equations, or visual elements present.',
                            'no visual elements present.',
                            'no diagrams or visual elements present.',
                            ''
                        ]:
                            descriptions.append(f"Page {page_num}: {description}")
                            logger.info(f"Added description for page {page_num}")
                        else:
                            logger.info(f"Skipped page {page_num} - no visual elements")
                
                if descriptions:
                    combined_description = ", ".join(descriptions)
                    logger.info(f"Combined VLM description created with {len(descriptions)} pages, total length: {len(combined_description)}")
                    logger.info(f"Final VLM description: {combined_description[:200]}...")
                    return combined_description
                else:
                    logger.warning("No pages with meaningful visual descriptions found")
                    return "No pages with meaningful visual descriptions found in vlm_json."
            
            else:
                logger.warning(f"vlm_json does not contain pages_data. Available keys: {list(vlm_data.keys()) if isinstance(vlm_data, dict) else 'Not a dict'}")
                return f"vlm_json does not contain pages_data structure."
            
        except Exception as e:
            error_msg = f"Error extracting VLM description from vlm_json: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def create_simple_page_storage(self, page_number, rubric_json):
        """Create a simple storage format: page number and parsed JSON"""
        return {
            'page_number': page_number,
            'rubric_json': rubric_json
        }

    def call_process_rubric_api(self, question_paper_uuid, rubric_data):
        """
        Call the process-rubric API to update the database with generated rubric data
        
        Args:
            question_paper_uuid (str): The UUID of the question paper
            rubric_data (dict): The complete rubric data structure
        
        Returns:
            dict: Success/failure result with API response
        """
        try:
            # Prepare the payload in the expected format
            payload = {
                "question_paper_uuid": str(question_paper_uuid),
                "input_data": {
                    "django_response": {
                        "data": {
                            "rubric_json": {
                                "individual_pages": rubric_data.get('individual_pages', [])
                            }
                        }
                    }
                }
            }
            
            headers = {
                'Content-Type': 'application/json',
            }
            
            logger.info(f"Calling process rubric API - URL: {self.process_rubric_api_url}")
            logger.info(f"Request headers: {headers}")
            logger.info(f"Payload structure - UUID: {question_paper_uuid}")
            logger.info(f"Payload structure - Individual pages count: {len(rubric_data.get('individual_pages', []))}")
            
            # Log the payload structure (without full content for brevity)
            logger.info(f"Full payload keys: {list(payload.keys())}")
            logger.info(f"Input data keys: {list(payload['input_data'].keys())}")
            logger.info(f"Django response keys: {list(payload['input_data']['django_response'].keys())}")
            
            response = requests.post(
                self.process_rubric_api_url,
                json=payload,
                headers=headers,
                timeout=60  # 1 minute timeout for processing
            )
            
            logger.info(f"Process rubric API response status: {response.status_code}")
            logger.info(f"Process rubric API response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                api_response = response.json()
                logger.info(f"Process rubric API successful response: {api_response}")
                return {
                    'success': True,
                    'response': api_response
                }
            else:
                error_text = response.text
                logger.error(f"Process rubric API error response: {error_text}")
                return {
                    'success': False,
                    'error': f'Process rubric API returned {response.status_code}',
                    'response': error_text
                }
                
        except requests.exceptions.RequestException as e:
            error_msg = f'Failed to connect to Process Rubric API: {str(e)}'
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f'Error calling Process Rubric API: {str(e)}'
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

    def process_rubric_generation(self, question_paper_uuid):
        """
        Main method to process rubric generation for a given UUID
        
        Args:
            question_paper_uuid (str): The UUID of the question paper
            
        Returns:
            dict: Result of the entire rubric generation process
        """
        try:
            # Step 1: Fetch data from Django database
            logger.info("Step 1: Fetching data from database...")
            fetch_result = self.fetch_qp_data_from_django(question_paper_uuid)
            
            if not fetch_result['success']:
                logger.error(f"Failed to fetch data from database: {fetch_result['error']}")
                return {
                    'success': False,
                    'error': 'Failed to fetch data from database',
                    'details': fetch_result['error']
                }
            
            qp_data = fetch_result['data']['data']
            logger.info(f"Successfully fetched QP data with keys: {list(qp_data.keys()) if isinstance(qp_data, dict) else 'Not a dict'}")
            
            # Check if OCR data exists
            if not qp_data.get('ocr_json'):
                logger.error("No OCR data found for this question paper UUID")
                return {
                    'success': False,
                    'error': 'No OCR data found for this question paper UUID'
                }
            
            ocr_data = qp_data['ocr_json']
            logger.info(f"OCR data keys: {list(ocr_data.keys()) if isinstance(ocr_data, dict) else 'Not a dict'}")
            
            # Step 2: Extract pages data
            if 'pages_data' not in ocr_data or not ocr_data['pages_data']:
                logger.error("No pages data found in OCR results")
                return {
                    'success': False,
                    'error': 'No pages data found in OCR results'
                }
            
            pages_data = ocr_data['pages_data']
            logger.info(f"Step 2: Found {len(pages_data)} pages to process")
            
            # Log page details
            for i, page_data in enumerate(pages_data):
                page_number = page_data.get('page_number', i + 1)
                page_text_length = len(page_data.get('full_text', ''))
                logger.info(f"Page {page_number}: text length = {page_text_length} characters")
            
            # Step 3: Extract VLM description from vlm_json field
            logger.info("Step 3: Extracting VLM description...")
            vlm_description = self.extract_vlm_description_from_data(qp_data)
            logger.info(f"VLM description extracted - length: {len(vlm_description)} characters")
            logger.info(f"VLM description preview: {vlm_description[:200]}...")
            
            # Step 4: Process each page and collect results in simplified format
            logger.info("Step 4: Processing pages for rubric generation...")
            simplified_page_results = []
            processing_errors = []
            
            for i, page_data in enumerate(pages_data):
                page_number = page_data.get('page_number', i + 1)
                page_text = page_data.get('full_text', '')
                
                logger.info(f"Processing page {page_number}...")
                logger.info(f"Page {page_number} text length: {len(page_text)} characters")
                
                if not page_text.strip():
                    error_msg = f"Page {page_number}: No text content found"
                    logger.warning(error_msg)
                    processing_errors.append(error_msg)
                    continue
                
                # Call rubric generation API for this page
                logger.info(f"Calling rubric generation API for page {page_number}")
                rubric_result = self.call_rubric_generation_api(page_text, vlm_description)
                
                if rubric_result['success']:
                    # Extract the parsed JSON rubric
                    rubric_json = rubric_result['result'].get('result', [])
                    logger.info(f"Page {page_number} rubric generation successful - result type: {type(rubric_json)}")
                    if isinstance(rubric_json, list):
                        logger.info(f"Page {page_number} rubric contains {len(rubric_json)} items")
                    
                    # Create simplified storage format
                    simple_page_result = self.create_simple_page_storage(page_number, rubric_json)
                    simplified_page_results.append(simple_page_result)
                    
                    logger.info(f"Successfully processed page {page_number}")
                else:
                    error_msg = f"Page {page_number}: {rubric_result['error']}"
                    logger.error(error_msg)
                    processing_errors.append(error_msg)
                
                # Add a small delay to avoid overwhelming the rubric API
                time.sleep(1)
            
            # Step 5: Prepare final simplified rubric data structure
            logger.info("Step 5: Preparing final rubric data structure...")
            rubric_json_data = {
                'question_paper_uuid': str(question_paper_uuid),
                'generation_timestamp': datetime.now().isoformat(),
                'vlm_description_source': 'vlm_json_field',  # Indicate source of VLM description
                'processing_summary': {
                    'total_pages': len(pages_data),
                    'successfully_processed': len(simplified_page_results),
                    'failed_pages': len(processing_errors),
                    'vlm_description_length': len(vlm_description)
                },
                'individual_pages': simplified_page_results,  # Simplified: just page_number and rubric_json
                'processing_errors': processing_errors
            }
            
            logger.info(f"Final rubric data structure prepared:")
            logger.info(f"  - Total pages: {len(pages_data)}")
            logger.info(f"  - Successfully processed: {len(simplified_page_results)}")
            logger.info(f"  - Failed pages: {len(processing_errors)}")
            logger.info(f"  - Processing errors: {processing_errors}")
            
            # Step 6: Call the process-rubric API to update the database
            logger.info("Step 6: Calling process-rubric API to update database...")
            process_result = self.call_process_rubric_api(question_paper_uuid, rubric_json_data)
            
            # Step 7: Prepare final response
            successful_pages = len(simplified_page_results)
            logger.info(f"Rubric generation completed successfully for {successful_pages} pages")
            
            processing_summary = {
                'total_pages': len(pages_data),
                'successful_pages': successful_pages,
                'failed_pages': len(pages_data) - successful_pages,
                'processing_errors_count': len(processing_errors),
                'vlm_description_found': bool(vlm_description and vlm_description != "No visual description available in database.")
            }
            
            sample_structure = {
                'description': 'Each page stored as: {page_number: int, rubric_json: array}',
                'example_page': simplified_page_results[0] if simplified_page_results else None
            }
            
            return {
                'success': True,
                'vlm_description_source': 'vlm_json_field',
                'processing_summary': processing_summary,
                'rubric_data': rubric_json_data,
                'database_update': process_result,
                'sample_structure': sample_structure
            }
            
        except Exception as e:
            logger.error(f"Process rubric generation failed with exception: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Process rubric generation failed: {str(e)}'
            }

    def check_health(self):
        """Check health of all external services"""
        try:
            # Check Django API connectivity
            django_status = False
            try:
                django_health = requests.get(f'{self.django_api_base_url}/status/', timeout=5)
                django_status = django_health.status_code == 200
            except:
                pass
            
            # Check Rubric API connectivity
            rubric_status = False
            try:
                rubric_health = requests.get(f'{self.rubric_generation_api_url.replace("/generate-rubric", "/health")}', timeout=5)
                rubric_status = rubric_health.status_code == 200
            except:
                pass
            
            # Check Process Rubric API connectivity
            process_rubric_status = False
            try:
                process_rubric_health = requests.get(f'{self.process_rubric_api_url.replace("/process-rubric/", "/health/")}', timeout=5)
                process_rubric_status = process_rubric_health.status_code == 200
            except:
                pass
            
            return {
                'success': True,
                'message': 'Rubric Generator Service is running',
                'timestamp': datetime.now().isoformat(),
                'external_services': {
                    'django_api': {
                        'status': 'connected' if django_status else 'disconnected',
                        'url': self.django_api_base_url
                    },
                    'rubric_generation_api': {
                        'status': 'connected' if rubric_status else 'disconnected',
                        'url': self.rubric_generation_api_url
                    },
                    'process_rubric_api': {
                        'status': 'connected' if process_rubric_status else 'disconnected',
                        'url': self.process_rubric_api_url
                    }
                }
            }
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                'success': False,
                'message': 'Health check failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def get_service_status(self):
        """Get detailed service status information"""
        try:
            health_check = self.check_health()
            
            return {
                'service_name': 'Rubric Generator Service',
                'version': '1.0.0',
                'timestamp': datetime.now().isoformat(),
                'configuration': {
                    'django_api_url': self.django_api_base_url,
                    'rubric_generation_api_url': self.rubric_generation_api_url,
                    'process_rubric_api_url': self.process_rubric_api_url,
                    'request_timeout': self.request_timeout
                },
                'health_check': health_check,
                'capabilities': [
                    'Fetch question paper data from Django API',
                    'Extract VLM descriptions from database',
                    'Generate rubrics using external API',
                    'Process and store rubric data',
                    'Health monitoring of external services'
                ]
            }
        except Exception as e:
            logger.error(f"Get service status failed: {str(e)}")
            return {
                'success': False,
                'error': f'Service status check failed: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }