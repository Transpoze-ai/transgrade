import json
from typing import Dict, Any, List, Tuple


def validate_ocr_json(ocr_data: Dict[Any, Any]) -> Tuple[bool, str]:
    """
    Validate OCR JSON structure
    Returns: (is_valid, error_message)
    """
    try:
        if not isinstance(ocr_data, dict):
            return False, "OCR data must be a JSON object"
        
        # Add your specific OCR validation logic here
        # This is a basic example - modify according to your OCR provider's format
        
        return True, ""
    except Exception as e:
        return False, f"Invalid OCR JSON: {str(e)}"


def extract_text_from_ocr_json(ocr_data: Dict[Any, Any]) -> str:
    """
    Extract plain text from OCR JSON
    Modify this function based on your OCR provider's JSON structure
    """
    try:
        if not ocr_data:
            return ""
        
        # Common OCR JSON structures - adjust based on your provider
        # Example for Google Vision API
        if 'textAnnotations' in ocr_data:
            return ocr_data['textAnnotations'][0].get('description', '')
        
        # Example for AWS Textract
        if 'Blocks' in ocr_data:
            text_blocks = [block.get('Text', '') for block in ocr_data['Blocks'] 
                          if block.get('BlockType') == 'LINE']
            return '\n'.join(text_blocks)
        
        # Generic fallback
        if 'text' in ocr_data:
            return ocr_data['text']
        
        if 'content' in ocr_data:
            return ocr_data['content']
            
        return ""
        
    except Exception as e:
        return ""


def extract_confidence_from_ocr_json(ocr_data: Dict[Any, Any]) -> float:
    """
    Extract confidence score from OCR JSON
    Modify this function based on your OCR provider's JSON structure
    """
    try:
        if not ocr_data:
            return 0.0
        
        # Common OCR JSON structures - adjust based on your provider
        if 'confidence' in ocr_data:
            return float(ocr_data['confidence'])
        
        if 'score' in ocr_data:
            return float(ocr_data['score'])
            
        # For Google Vision API
        if 'textAnnotations' in ocr_data and ocr_data['textAnnotations']:
            return ocr_data['textAnnotations'][0].get('confidence', 0.0)
        
        return 0.0
        
    except Exception as e:
        return 0.0


def format_ocr_json_for_display(ocr_data: Dict[Any, Any]) -> str:
    """
    Format OCR JSON for better display in admin or API responses
    """
    try:
        return json.dumps(ocr_data, indent=2, ensure_ascii=False)
    except Exception as e:
        return str(ocr_data)


def process_ocr_batch(ocr_batch: List[Dict[Any, Any]]) -> List[Dict[str, Any]]:
    """
    Process a batch of OCR data for bulk operations
    """
    processed_batch = []
    
    for ocr_item in ocr_batch:
        try:
            processed_item = {
                'original': ocr_item,
                'text': extract_text_from_ocr_json(ocr_item),
                'confidence': extract_confidence_from_ocr_json(ocr_item),
                'is_valid': validate_ocr_json(ocr_item)[0]
            }
            processed_batch.append(processed_item)
        except Exception as e:
            processed_batch.append({
                'original': ocr_item,
                'text': '',
                'confidence': 0.0,
                'is_valid': False,
                'error': str(e)
            })
    
    return processed_batch