"""
OCR Semantic Chunker Service
Service class for handling OCR semantic chunking with LLM analysis
"""

import requests
import json
import logging
import time
import openai
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from config import Config

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class ChunkBoundary:
    line_index: int
    confidence: float
    reason: str
    boundary_type: str
    text_before: str
    text_after: str

class OCRSemanticChunker:
    def __init__(self, api_key: str):
        """
        Initialize the OCR Semantic Chunker with OpenAI API key
        
        Args:
            api_key: Your OpenAI API key
        """
        self.client = openai.OpenAI(api_key=api_key)

    def process_ocr_data(self, ocr_data: List[Dict]) -> List[str]:
        """
        Convert OCR bounding box data into ordered text lines
        
        Args:
            ocr_data: List of OCR objects with 'text', 'confidence', and 'boundingBox'
            
        Returns:
            List of text lines in reading order
        """
        print(f"Processing {len(ocr_data)} OCR items...")
        
        # Filter out low confidence items (optional - adjust threshold as needed)
        CONFIDENCE_THRESHOLD = 0.2
        filtered_items = []
        
        for item in ocr_data:
            if item.get('confidence', 0) >= CONFIDENCE_THRESHOLD:
                text = item['text'].strip()
                if text:  # Only include non-empty text
                    bbox = item['boundingBox']
                    if len(bbox) >= 4:
                        # Handle bounding box format [x1, y1, x2, y2]
                        x1, y1, x2, y2 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
                        
                        filtered_items.append({
                            'text': text,
                            'confidence': item['confidence'],
                            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                            'center_x': (x1 + x2) / 2,
                            'center_y': (y1 + y2) / 2,
                            'height': abs(y2 - y1),
                            'bbox': bbox
                        })
        
        print(f"Filtered to {len(filtered_items)} high-confidence items")
        
        if not filtered_items:
            return []
        
        # Sort by Y position first (top to bottom), then X position (left to right)
        filtered_items.sort(key=lambda x: (x['center_y'], x['center_x']))
        
        # Group items into lines based on Y-coordinate proximity
        lines = self._group_into_lines(filtered_items)
        
        print(f"Organized into {len(lines)} text lines")
        return lines

    def _group_into_lines(self, items: List[Dict]) -> List[str]:
        """Group OCR items into text lines based on Y-coordinate proximity"""
        if not items:
            return []
        
        # Calculate average height for tolerance
        heights = [item['height'] for item in items if item['height'] > 0]
        avg_height = np.mean(heights) if heights else 20
        
        # Calculate Y-tolerance for grouping items into lines
        Y_TOLERANCE = max(avg_height * 0.6, 15)  # Generous tolerance
        
        print(f"Using Y-tolerance of {Y_TOLERANCE:.1f} pixels (avg height: {avg_height:.1f})")
        
        # Group items by similar Y coordinates
        line_groups = []
        
        for item in items:
            # Find best matching line group
            best_group = None
            best_distance = float('inf')
            
            for group in line_groups:
                if group:
                    # Calculate median Y of current group
                    group_y_values = [g['center_y'] for g in group]
                    group_y_median = np.median(group_y_values)
                    
                    distance = abs(item['center_y'] - group_y_median)
                    if distance <= Y_TOLERANCE and distance < best_distance:
                        best_group = group
                        best_distance = distance
            
            if best_group is not None:
                best_group.append(item)
            else:
                line_groups.append([item])
        
        # Sort line groups by Y position (top to bottom)
        line_groups.sort(key=lambda group: np.median([item['center_y'] for item in group]))
        
        # Convert each line group to text
        lines = []
        for group in line_groups:
            # Sort items in line by X position (left to right)
            group.sort(key=lambda x: x['center_x'])
            
            # Join text with intelligent spacing
            line_text = self._join_line_text(group)
            if line_text:
                lines.append(line_text)
        
        return lines

    def _join_line_text(self, line_items: List[Dict]) -> str:
        """Intelligently join text items in a line with proper spacing"""
        if not line_items:
            return ""
        
        if len(line_items) == 1:
            return line_items[0]['text']
        
        result_parts = [line_items[0]['text']]
        
        for i in range(1, len(line_items)):
            current = line_items[i]
            previous = line_items[i-1]
            
            # Calculate horizontal gap
            gap = current['x1'] - previous['x2']
            
            # Decide on spacing
            needs_space = True
            
            # No space for punctuation
            if current['text'] and current['text'][0] in '.,!?:;)]}>':
                needs_space = False
            # No space after opening brackets/quotes
            elif result_parts[-1] and result_parts[-1][-1] in '([{<"\'':
                needs_space = False
            # No space for very small gaps (touching text)
            elif gap < 2:
                needs_space = False
            
            # Add appropriate spacing
            if gap > 50:  # Large gap - multiple spaces
                result_parts.append('  ')
            elif needs_space and gap > 1:
                result_parts.append(' ')
            
            result_parts.append(current['text'])
        
        return ''.join(result_parts).strip()

    def identify_semantic_boundaries(self, lines: List[str]) -> List[ChunkBoundary]:
        """
        Use LLM to identify semantic boundaries for intelligent chunking
        
        Args:
            lines: List of text lines from OCR processing
            
        Returns:
            List of ChunkBoundary objects indicating where to split content
        """
        if not lines or len(lines) < 2:
            return []
        
        # Prepare numbered lines for analysis
        numbered_lines = [f"Line {i+1}: {line}" for i, line in enumerate(lines)]
        text_to_analyze = '\n'.join(numbered_lines)
        
        prompt = f"""Analyze this OCR-extracted text and identify semantic boundaries for intelligent chunking.

Text to analyze:
{text_to_analyze}

Identify natural breaking points where content could be meaningfully separated. Focus on:

## PRIMARY BOUNDARIES (High Priority - Confidence 0.8-1.0):
- **ANSWER_START**: Beginning of numbered answers (e.g., "1.", "A.1.", "Q1:", "Answer:")  
- **QUESTION_START**: Beginning of new questions or prompts
- **SECTION_HEADER**: Major sections (e.g., "PART A", "Section I", subject names)
- **TOPIC_CHANGE**: Clear subject matter changes

## SECONDARY BOUNDARIES (Medium Priority - Confidence 0.5-0.7):
- **SUBSECTION_START**: Sub-parts within answers (e.g., "(i)", "(a)", bullet points)
- **PARAGRAPH_BREAK**: Logical paragraph divisions in long text
- **DEFINITION_START**: Beginning of definitions or key concepts
- **EXAMPLE_START**: Beginning of examples or illustrations

## DETECTION PATTERNS:
1. **Numbering**: "1.", "2)", "(a)", "(i)", "Q1", etc.
2. **Keywords**: "Answer", "Solution", "Definition", "Example", "Explanation"
3. **Section markers**: "PART", "SECTION", "CHAPTER", "UNIT"
4. **Question indicators**: "What", "How", "Why", "Define", "Explain"
5. **Answer patterns**: "A:", "Ans:", "Solution:", direct responses

## IGNORE:
- Headers with school names, dates, student info
- Page numbers, administrative text
- Minor line breaks within sentences
- Signature lines

Return a JSON array with boundary objects containing:
- "line_number": 1-based line number where boundary occurs
- "boundary_type": Exact type from categories above  
- "confidence": 0.0-1.0 confidence score
- "reason": Specific explanation of why this is a boundary
- "text_before": Last 15 chars before boundary (or empty if line 1)
- "text_after": First 15 chars at boundary

Focus on educational content structure. Return empty array [] if no clear boundaries found.

Example: [{{"line_number": 3, "boundary_type": "ANSWER_START", "confidence": 0.9, "reason": "Line starts with '1. A)' indicating numbered answer", "text_before": "examination", "text_after": "1. A) Everything"}}]"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing educational documents and identifying semantic boundaries for intelligent text chunking. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Clean JSON response
            if response_text.startswith('```json'):
                response_text = response_text.split('\n', 1)[1].rsplit('\n```', 1)[0]
            elif response_text.startswith('```'):
                response_text = response_text.split('\n', 1)[1].rsplit('\n', 1)[0]
            
            boundaries_data = json.loads(response_text)
            
            # Convert to ChunkBoundary objects
            boundaries = []
            for b in boundaries_data:
                # Validate line number
                line_num = int(b['line_number'])
                if 1 <= line_num <= len(lines):
                    boundary = ChunkBoundary(
                        line_index=line_num - 1,  # Convert to 0-based
                        confidence=float(b['confidence']),
                        reason=b['reason'],
                        boundary_type=b['boundary_type'],
                        text_before=b.get('text_before', ''),
                        text_after=b.get('text_after', '')
                    )
                    boundaries.append(boundary)
            
            # Sort by line index
            boundaries.sort(key=lambda x: x.line_index)
            print(f"Identified {len(boundaries)} semantic boundaries")
            
            return boundaries
            
        except Exception as e:
            print(f"LLM boundary detection failed: {e}")
            return []

    def create_semantic_chunks(self, lines: List[str], boundaries: List[ChunkBoundary], 
                             max_chunk_size: int = 1500) -> List[Dict[str, Any]]:
        """
        Create semantic chunks based on identified boundaries
        
        Args:
            lines: Text lines to chunk
            boundaries: Semantic boundaries from LLM analysis
            max_chunk_size: Maximum characters per chunk (fallback)
            
        Returns:
            List of chunk dictionaries with metadata
        """
        if not lines:
            return []
        
        chunks = []
        current_chunk_lines = []
        chunk_start_line = 0
        
        # Filter boundaries by confidence threshold
        high_conf_boundaries = [b for b in boundaries if b.confidence >= 0.6]
        print(f"Using {len(high_conf_boundaries)} high-confidence boundaries")
        
        for line_idx, line in enumerate(lines):
            # Check if this line is a semantic boundary
            should_break = False
            boundary_info = None
            
            for boundary in high_conf_boundaries:
                if boundary.line_index == line_idx and current_chunk_lines:
                    should_break = True
                    boundary_info = boundary
                    break
            
            # Create chunk before this boundary
            if should_break:
                chunk_text = '\n'.join(current_chunk_lines).strip()
                if chunk_text:
                    chunks.append({
                        'text': chunk_text,
                        'length': len(chunk_text),
                        'line_count': len(current_chunk_lines),
                        'start_line': chunk_start_line + 1,  # 1-based for display
                        'end_line': line_idx,
                        'boundary_type': boundary_info.boundary_type if boundary_info else 'UNKNOWN',
                        'boundary_reason': boundary_info.reason if boundary_info else '',
                        'confidence': boundary_info.confidence if boundary_info else 0.0
                    })
                
                current_chunk_lines = []
                chunk_start_line = line_idx
            
            # Add current line to chunk
            current_chunk_lines.append(line)
            
            # Size-based fallback splitting
            current_text = '\n'.join(current_chunk_lines)
            if len(current_text) > max_chunk_size and len(current_chunk_lines) > 1:
                # Save all but last line
                chunk_lines = current_chunk_lines[:-1]
                chunk_text = '\n'.join(chunk_lines).strip()
                
                chunks.append({
                    'text': chunk_text,
                    'length': len(chunk_text),
                    'line_count': len(chunk_lines),
                    'start_line': chunk_start_line + 1,
                    'end_line': line_idx,
                    'boundary_type': 'SIZE_LIMIT',
                    'boundary_reason': 'Chunk exceeded maximum size',
                    'confidence': 1.0
                })
                
                # Keep last line for next chunk
                current_chunk_lines = [current_chunk_lines[-1]]
                chunk_start_line = line_idx
        
        # Handle remaining lines
        if current_chunk_lines:
            chunk_text = '\n'.join(current_chunk_lines).strip()
            if chunk_text:
                chunks.append({
                    'text': chunk_text,
                    'length': len(chunk_text),
                    'line_count': len(current_chunk_lines),
                    'start_line': chunk_start_line + 1,
                    'end_line': len(lines),
                    'boundary_type': 'DOCUMENT_END',
                    'boundary_reason': 'End of document',
                    'confidence': 1.0
                })
        
        print(f"Created {len(chunks)} semantic chunks")
        return chunks

    def chunk_ocr_document(self, ocr_data: List[Dict], max_chunk_size: int = 1500) -> List[Dict[str, str]]:
        """
        Main function: Process OCR data and create semantic chunks
        
        Args:
            ocr_data: List of OCR objects with 'text', 'confidence', 'boundingBox'
            max_chunk_size: Maximum characters per chunk (fallback limit)
            
        Returns:
            List of chunks in format: [{"chunk_id": "C1", "chunk_text": "..."}]
        """
        print("Starting OCR document chunking process...")
        
        # Step 1: Convert OCR data to ordered text lines
        lines = self.process_ocr_data(ocr_data)
        if not lines:
            print("No text lines extracted from OCR data")
            return []
        
        print(f"Extracted {len(lines)} lines of text")
        
        # Step 2: Identify semantic boundaries using LLM
        boundaries = self.identify_semantic_boundaries(lines)
        
        # Step 3: Create chunks based on boundaries
        chunks = self.create_semantic_chunks(lines, boundaries, max_chunk_size)
        
        # Step 4: Format output as required
        formatted_chunks = []
        for i, chunk in enumerate(chunks, 1):
            formatted_chunks.append({
                "chunk_id": f"C{i}",
                "chunk_text": chunk['text']
            })
        
        print(f"Successfully created {len(formatted_chunks)} semantic chunks")
        return formatted_chunks

class ChunkerService:
    """Service class for handling chunker operations"""
    
    def __init__(self):
        self.django_base_url = Config. DJANGO_OCR_FETCH
        self.webhook_url = Config.WEBHOOK_CHUNK_URL
        self.webhook_timeout = Config.WEBHOOK_TIMEOUT
        self.webhook_max_retries = Config.WEBHOOK_MAX_RETRIES
        
        # Build Django API endpoint pattern
        if self.django_base_url:
            # Remove the extra /answer-scripts path - the correct URL is just /ocr-data/
            self.django_api_endpoint = f"{self.django_base_url}/ocr-data/roll/{{roll_no}}/uuid/{{question_paper_uuid}}"
        else:
            self.django_api_endpoint = None

    def extract_ocr_data(self, ocr_json_data: Dict) -> List[Dict]:
        """
        Extract OCR data from various possible JSON structures
        
        Args:
            ocr_json_data: Raw OCR JSON data from database
            
        Returns:
            List of OCR items with 'text', 'confidence', 'boundingBox'
        """
        if not isinstance(ocr_json_data, dict):
            return []
        
        # Try different possible structures in your OCR JSON
        possible_keys = ['extracted_text', 'text_items', 'ocr_results', 'results', 'data']
        
        for key in possible_keys:
            if key in ocr_json_data and isinstance(ocr_json_data[key], list):
                data = ocr_json_data[key]
                if data and self.is_valid_ocr_data(data):
                    return data
        
        # Check if the entire JSON is already a list
        if isinstance(ocr_json_data, list) and self.is_valid_ocr_data(ocr_json_data):
            return ocr_json_data
        
        # Try to find any list that contains valid OCR data
        for value in ocr_json_data.values():
            if isinstance(value, list) and value and self.is_valid_ocr_data(value):
                return value
        
        return []

    def is_valid_ocr_data(self, data: List) -> bool:
        """
        Check if a list contains valid OCR data structure
        
        Args:
            data: List to check
            
        Returns:
            True if valid OCR data, False otherwise
        """
        if not data:
            return False
        
        first_item = data[0]
        if not isinstance(first_item, dict):
            return False
        
        # Check for required fields
        required_fields = ['text', 'boundingBox']
        has_required = all(field in first_item for field in required_fields)
        
        # Check if boundingBox has correct format
        if has_required and 'boundingBox' in first_item:
            bbox = first_item['boundingBox']
            if isinstance(bbox, list) and len(bbox) >= 4:
                return True
        
        return False

    def validate_webhook_url(self, url: str) -> bool:
        """Validate webhook URL format and accessibility"""
        try:
            logger.debug(f"Validating webhook URL: {url}")
            
            # Basic URL format validation
            if not url.startswith(('http://', 'https://')):
                logger.debug(f"Invalid URL scheme: {url}")
                return False
            
            # Test basic connectivity with HEAD request
            response = requests.head(url, timeout=10)
            logger.debug(f"HEAD request status: {response.status_code}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.debug(f"URL validation failed: {str(e)}")
            return False
        except Exception as e:
            logger.debug(f"Unexpected validation error: {str(e)}")
            return False

    def send_webhook_notification(self, webhook_url: str, data: dict, max_retries: int = None) -> bool:
        """Send chunk results to webhook URL with retry logic and debugging"""
        if max_retries is None:
            max_retries = self.webhook_max_retries
            
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Chunker-API/1.0'
        }
        
        logger.debug(f"Webhook payload size: {len(str(data))} characters")
        logger.debug(f"Webhook payload keys: {list(data.keys())}")
        if 'total_chunks' in data:
            logger.debug(f"Total chunks being sent: {data['total_chunks']}")
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Sending webhook notification (attempt {attempt + 1}/{max_retries})")
                logger.info(f"Webhook URL: {webhook_url}")
                
                response = requests.post(
                    webhook_url, 
                    json=data, 
                    headers=headers,
                    timeout=self.webhook_timeout
                )
                
                logger.info(f"Webhook response status: {response.status_code}")
                logger.debug(f"Response time: {response.elapsed.total_seconds():.2f} seconds")
                
                if response.status_code in [200, 201, 202]:
                    logger.info("Webhook notification sent successfully")
                    return True
                else:
                    logger.warning(f"Webhook returned non-success status: {response.status_code}")
                    logger.debug(f"Error response body: {response.text}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Webhook timeout on attempt {attempt + 1}")
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Webhook connection error on attempt {attempt + 1}: {str(e)}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Webhook request error on attempt {attempt + 1}: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected webhook error on attempt {attempt + 1}: {str(e)}")
                import traceback
                logger.debug(f"Full traceback:\n{traceback.format_exc()}")
            
            if attempt < max_retries - 1:
                logger.info("Retrying webhook in 2 seconds...")
                time.sleep(2)
        
        logger.error("Failed to send webhook notification after all retries")
        return False

    def process_ocr_chunks(self, question_paper_uuid: str, roll_no: str, 
                          openai_api_key: str, max_chunk_size: int = 1500) -> Dict:
        """
        Main processing function: Fetch OCR data and create semantic chunks
        
        Args:
            question_paper_uuid: UUID of the question paper
            roll_no: Student roll number
            openai_api_key: OpenAI API key for LLM analysis
            max_chunk_size: Maximum characters per chunk
            
        Returns:
            Dictionary with processing results
        """
        # Step 1: Fetch OCR data from Django API
        if not self.django_api_endpoint:
            return {
                'success': False,
                'error': 'Django API base URL not configured',
                'question_paper_uuid': question_paper_uuid,
                'roll_no': roll_no,
                'total_pages': 0,
                'total_chunks': 0,
                'chunks': [],
                'page_info': []
            }
        
        django_url = self.django_api_endpoint.format(
            roll_no=roll_no,
            question_paper_uuid=question_paper_uuid
        )
        
        logger.info(f"Fetching data from Django API: {django_url}")
        
        try:
            response = requests.get(django_url, timeout=30)
            response.raise_for_status()
            django_data = response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch data from Django API: {e}")
            return {
                'success': False,
                'error': f'Failed to fetch OCR data from Django API: {str(e)}',
                'question_paper_uuid': question_paper_uuid,
                'roll_no': roll_no,
                'total_pages': 0,
                'total_chunks': 0,
                'chunks': [],
                'page_info': []
            }
        
        if not django_data.get('success', False):
            logger.error(f"Django API returned error: {django_data.get('error', 'Unknown error')}")
            return {
                'success': False,
                'error': f"No OCR data found for UUID: {question_paper_uuid} and Roll No: {roll_no}",
                'question_paper_uuid': question_paper_uuid,
                'roll_no': roll_no,
                'total_pages': 0,
                'total_chunks': 0,
                'chunks': [],
                'page_info': []
            }
        
        ocr_records = django_data.get('data', [])
        if not ocr_records:
            return {
                'success': False,
                'error': "No OCR records found in the response",
                'question_paper_uuid': question_paper_uuid,
                'roll_no': roll_no,
                'total_pages': 0,
                'total_chunks': 0,
                'chunks': [],
                'page_info': []
            }
        
        logger.info(f"Found {len(ocr_records)} pages of OCR data")
        
        # Step 2: Initialize semantic chunker with LLM capabilities
        try:
            chunker = OCRSemanticChunker(openai_api_key)
        except Exception as e:
            logger.error(f"Failed to initialize OCR chunker: {e}")
            return {
                'success': False,
                'error': f'Failed to initialize OCR chunker with OpenAI API: {str(e)}',
                'question_paper_uuid': question_paper_uuid,
                'roll_no': roll_no,
                'total_pages': 0,
                'total_chunks': 0,
                'chunks': [],
                'page_info': []
            }
        
        # Step 3: Process each page and collect chunks
        all_chunks = []
        page_info = []
        
        for ocr_record in ocr_records:
            page_number = ocr_record.get('page_number')
            ocr_json_data = ocr_record.get('ocr_json_dump', {})
            
            logger.info(f"Processing page {page_number} with LLM semantic analysis...")
            
            # Extract OCR data from the JSON structure
            page_ocr_data = self.extract_ocr_data(ocr_json_data)
            
            if not page_ocr_data:
                logger.warning(f"No valid OCR data found for page {page_number}")
                page_info.append({
                    'page_number': page_number,
                    'chunks_count': 0,
                    'status': 'No valid OCR data',
                    'chunk_ids': []
                })
                continue
            
            logger.info(f"Found {len(page_ocr_data)} OCR items on page {page_number}")
            
            # Process page through semantic chunker with LLM analysis
            try:
                page_chunks = chunker.chunk_ocr_document(page_ocr_data, max_chunk_size)
                
                if page_chunks:
                    # Adjust chunk IDs to be globally unique
                    current_chunk_count = len(all_chunks)
                    chunk_ids = []
                    
                    for i, chunk in enumerate(page_chunks):
                        new_chunk_id = f"C{current_chunk_count + i + 1}"
                        chunk['chunk_id'] = new_chunk_id
                        chunk_ids.append(new_chunk_id)
                        all_chunks.append(chunk)
                    
                    page_info.append({
                        'page_number': page_number,
                        'chunks_count': len(page_chunks),
                        'status': 'Success - LLM Analyzed',
                        'chunk_ids': chunk_ids
                    })
                    
                    logger.info(f"Created {len(page_chunks)} LLM-analyzed chunks for page {page_number}")
                else:
                    logger.warning(f"No chunks created for page {page_number}")
                    page_info.append({
                        'page_number': page_number,
                        'chunks_count': 0,
                        'status': 'No chunks created',
                        'chunk_ids': []
                    })
                    
            except Exception as e:
                logger.error(f"Error processing page {page_number}: {e}")
                page_info.append({
                    'page_number': page_number,
                    'chunks_count': 0,
                    'status': f'Error: {str(e)}',
                    'chunk_ids': []
                })
        
        logger.info(f"Successfully created {len(all_chunks)} total semantic chunks from {len(ocr_records)} pages")
        
        response_data = {
            'success': True,
            'question_paper_uuid': question_paper_uuid,
            'roll_no': roll_no,
            'total_pages': len(ocr_records),
            'total_chunks': len(all_chunks),
            'chunks': all_chunks,
            'page_info': page_info,
            'processing_summary': {
                'status': 'completed',
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
                'llm_analysis': True,
                'semantic_chunking': True,
                'total_chunks_created': len(all_chunks),
                'pages_processed': len(ocr_records)
            }
        }

        # Send webhook notification
        if self.webhook_url:
            logger.debug("Starting webhook notification process")
            url_valid = self.validate_webhook_url(self.webhook_url)
            logger.debug(f"Webhook URL validation result: {url_valid}")

            if url_valid:
                logger.info("Attempting to send webhook notification...")
                webhook_success = self.send_webhook_notification(self.webhook_url, response_data)
                
                if webhook_success:
                    logger.info("Webhook notification sent successfully")
                    response_data['webhook_status'] = 'sent'
                else:
                    logger.error("Failed to send webhook notification")
                    response_data['webhook_status'] = 'failed'
            else:
                logger.warning("Webhook URL validation failed, skipping notification")
                response_data['webhook_status'] = 'skipped_invalid_url'
        else:
            logger.info("No webhook URL configured")
            response_data['webhook_status'] = 'not_configured'

        return response_data

    def test_django_connection(self) -> Dict:
        """Test connection to Django API"""
        if not self.django_base_url:
            return {
                "status": "error",
                "django_url": None,
                "error": "Django API base URL not configured",
                "message": "Django API connection test failed"
            }
        
        try:
            test_url = f"{self.django_base_url}/ocr_data/"
            response = requests.get(test_url, timeout=10)
            response.raise_for_status()
            return {
                "status": "success",
                "django_url": self.django_base_url,
                "response_status": response.status_code,
                "message": "Django API connection successful"
            }
        except Exception as e:
            return {
                "status": "error",
                "django_url": self.django_base_url,
                "error": str(e),
                "message": "Django API connection failed"
            }

    def test_openai_connection(self, api_key: str) -> Dict:
        """Test OpenAI API connection"""
        try:
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello, this is a test."}],
                max_tokens=10
            )
            return {
                "status": "success",
                "message": "OpenAI API connection successful",
                "model": "gpt-3.5-turbo"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "OpenAI API test failed"
            }