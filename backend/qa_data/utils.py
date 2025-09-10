from typing import Dict, Any, List, Optional
from datetime import datetime


def parse_processing_timestamp(timestamp_str: str) -> Optional[datetime]:
    """
    Parse processing timestamp string to datetime object
    """
    if not timestamp_str:
        return None
        
    try:
        # Try ISO format first
        if 'T' in timestamp_str:
            # Remove 'Z' and add timezone if needed
            cleaned_timestamp = timestamp_str.replace('Z', '+00:00')
            return datetime.fromisoformat(cleaned_timestamp)
        
        # Fallback to basic parsing
        return datetime.fromisoformat(timestamp_str)
        
    except Exception as e:
        print(f"Failed to parse timestamp '{timestamp_str}': {e}")
        # Return None instead of current time to avoid confusion
        return None


def extract_qa_statistics(qa_mapping: List[Dict[Any, Any]]) -> Dict[str, Any]:
    """
    Extract statistics from QA mapping
    """
    if not qa_mapping or not isinstance(qa_mapping, list):
        return {
            'total_questions': 0,
            'answered_questions': 0,
            'parsing_errors': 0,
            'completion_rate': 0
        }
    
    total_questions = len(qa_mapping)
    answered_questions = 0
    parsing_errors = 0
    
    for item in qa_mapping:
        if isinstance(item, dict) and 'student_answer' in item:
            student_answer = item['student_answer']
            if isinstance(student_answer, str):
                if student_answer.strip() == 'PARSING_ERROR':
                    parsing_errors += 1
                elif student_answer.strip():  # Non-empty answer
                    answered_questions += 1
            else:
                # If student_answer is not a string, count as answered
                answered_questions += 1
    
    completion_rate = (answered_questions / total_questions * 100) if total_questions > 0 else 0
    
    return {
        'total_questions': total_questions,
        'answered_questions': answered_questions,
        'parsing_errors': parsing_errors,
        'completion_rate': round(completion_rate, 2)
    }