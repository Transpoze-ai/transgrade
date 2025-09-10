# ============================================================================
# qp_data/utils.py
# ============================================================================

import json
from typing import Dict, Any, List, Tuple


def validate_qp_json(json_data: Dict[Any, Any], json_type: str = "generic") -> Tuple[bool, str]:
    """
    Validate QP JSON structure
    Args:
        json_data: The JSON data to validate
        json_type: Type of JSON ('ocr', 'rubric', 'reference', or 'vlm')
    Returns: (is_valid, error_message)
    """
    try:
        if not isinstance(json_data, (dict, list)):
            return False, f"{json_type.upper()} data must be a JSON object or array"
        
        # Add specific validation logic based on json_type
        if json_type == "ocr":
            return validate_ocr_json_structure(json_data)
        elif json_type == "rubric":
            return validate_rubric_json_structure(json_data)
        elif json_type == "reference":
            return validate_reference_json_structure(json_data)
        elif json_type == "vlm":
            return validate_vlm_json_structure(json_data)
        
        return True, ""
    except Exception as e:
        return False, f"Invalid {json_type.upper()} JSON: {str(e)}"


def validate_ocr_json_structure(ocr_data: Dict[Any, Any]) -> Tuple[bool, str]:
    """Validate OCR JSON structure"""
    try:
        # Add your specific OCR validation logic here
        # This is a basic example - modify according to your ML model's OCR format
        if isinstance(ocr_data, dict):
            # Example: Check for required fields
            # if 'questions' not in ocr_data:
            #     return False, "OCR JSON must contain 'questions' field"
            pass
        
        return True, ""
    except Exception as e:
        return False, f"Invalid OCR JSON structure: {str(e)}"


def validate_rubric_json_structure(rubric_data: Dict[Any, Any]) -> Tuple[bool, str]:
    """Validate Rubric JSON structure"""
    try:
        # Add your specific Rubric validation logic here
        # This is a basic example - modify according to your ML model's Rubric format
        if isinstance(rubric_data, dict):
            # Example: Check for required fields
            # if 'grading_criteria' not in rubric_data:
            #     return False, "Rubric JSON must contain 'grading_criteria' field"
            pass
        
        return True, ""
    except Exception as e:
        return False, f"Invalid Rubric JSON structure: {str(e)}"


def validate_reference_json_structure(reference_data: Dict[Any, Any]) -> Tuple[bool, str]:
    """Validate Reference JSON structure"""
    try:
        # Add your specific Reference validation logic here
        # This is a basic example - modify according to your ML model's Reference format
        if isinstance(reference_data, dict):
            # Example: Check for required fields
            # if 'reference_answers' not in reference_data:
            #     return False, "Reference JSON must contain 'reference_answers' field"
            pass
        
        return True, ""
    except Exception as e:
        return False, f"Invalid Reference JSON structure: {str(e)}"


def validate_vlm_json_structure(vlm_data: Dict[Any, Any]) -> Tuple[bool, str]:
    """Validate VLM JSON structure"""
    try:
        # Add your specific VLM validation logic here
        # This is a basic example - modify according to your ML model's VLM format
        if isinstance(vlm_data, dict):
            # Example: Check for required fields
            # if 'visual_analysis' not in vlm_data:
            #     return False, "VLM JSON must contain 'visual_analysis' field"
            pass
        
        return True, ""
    except Exception as e:
        return False, f"Invalid VLM JSON structure: {str(e)}"


def format_qp_json_for_display(json_data: Dict[Any, Any]) -> str:
    """Format QP JSON for better display in admin or API responses"""
    try:
        return json.dumps(json_data, indent=2, ensure_ascii=False)
    except Exception as e:
        return str(json_data)


def extract_questions_from_ocr(ocr_data: Dict[Any, Any]) -> List[str]:
    """
    Extract questions from OCR JSON
    Modify this function based on your ML model's OCR format
    """
    try:
        questions = []
        if isinstance(ocr_data, dict):
            # Example implementation - modify based on your OCR structure
            if 'questions' in ocr_data:
                for q in ocr_data['questions']:
                    if isinstance(q, dict) and 'text' in q:
                        questions.append(q['text'])
                    elif isinstance(q, str):
                        questions.append(q)
        return questions
    except Exception as e:
        return []


def extract_grading_criteria_from_rubric(rubric_data: Dict[Any, Any]) -> List[Dict[str, Any]]:
    """
    Extract grading criteria from Rubric JSON
    Modify this function based on your ML model's Rubric format
    """
    try:
        criteria = []
        if isinstance(rubric_data, dict):
            # Example implementation - modify based on your Rubric structure
            if 'grading_criteria' in rubric_data:
                criteria = rubric_data['grading_criteria']
            elif 'criteria' in rubric_data:
                criteria = rubric_data['criteria']
        return criteria
    except Exception as e:
        return []


def extract_reference_answers_from_reference(reference_data: Dict[Any, Any]) -> List[Dict[str, Any]]:
    """
    Extract reference answers from Reference JSON
    Modify this function based on your ML model's Reference format
    """
    try:
        answers = []
        if isinstance(reference_data, dict):
            # Example implementation - modify based on your Reference structure
            if 'reference_answers' in reference_data:
                answers = reference_data['reference_answers']
            elif 'answers' in reference_data:
                answers = reference_data['answers']
        return answers
    except Exception as e:
        return []


def extract_visual_analysis_from_vlm(vlm_data: Dict[Any, Any]) -> List[Dict[str, Any]]:
    """
    Extract visual analysis from VLM JSON
    Modify this function based on your ML model's VLM format
    """
    try:
        analysis = []
        if isinstance(vlm_data, dict):
            # Example implementation - modify based on your VLM structure
            if 'visual_analysis' in vlm_data:
                analysis = vlm_data['visual_analysis']
            elif 'analysis' in vlm_data:
                analysis = vlm_data['analysis']
            elif 'vision_results' in vlm_data:
                analysis = vlm_data['vision_results']
        return analysis
    except Exception as e:
        return []