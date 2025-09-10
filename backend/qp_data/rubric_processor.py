from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class RubricProcessor:
    """
    Processes rubric JSON data and extracts rubric_json and reference_json
    Based on the logic from rubric_db_updater.py script
    """
    
    @staticmethod
    def extract_and_combine_rubric(input_json: Dict[Any, Any]) -> List[Dict[Any, Any]]:
        """
        Extract rubric_json items from all pages and combine them into a single list.
        """
        combined_rubric = []
        
        try:
            # Try different possible structures for individual_pages
            individual_pages = None
            
            # Method 1: django_response structure
            try:
                individual_pages = input_json["django_response"]["data"]["rubric_json"]["individual_pages"]
            except KeyError:
                pass
            
            # Method 2: direct individual_pages
            if not individual_pages:
                individual_pages = input_json.get("individual_pages", [])
            
            # Method 3: nested rubric_json structure
            if not individual_pages:
                try:
                    individual_pages = input_json["rubric_json"]["individual_pages"]
                except KeyError:
                    pass
            
            # Method 4: if input_json itself is a list of pages
            if not individual_pages and isinstance(input_json, list):
                individual_pages = input_json
            
            # Method 5: if input_json has 'pages' key
            if not individual_pages:
                individual_pages = input_json.get("pages", [])
            
            if not individual_pages:
                logger.warning("No individual_pages found in input JSON")
                return []
            
            # Process each page
            for i, page in enumerate(individual_pages):
                if not isinstance(page, dict):
                    continue
                    
                rubric_json = page.get("rubric_json", [])
                
                # Handle different rubric_json structures
                if isinstance(rubric_json, list):
                    for rubric_item in rubric_json:
                        combined_rubric.append(rubric_item)
                elif isinstance(rubric_json, dict):
                    combined_rubric.append(rubric_json)
            
            logger.info(f"Successfully extracted {len(combined_rubric)} rubric items from {len(individual_pages)} pages")
            
        except Exception as e:
            logger.error(f"Error extracting rubric data: {e}")
            return []
        
        return combined_rubric

    @staticmethod
    def extract_and_combine_qa(rubric_items: List[Dict[Any, Any]]) -> List[Dict[str, str]]:
        """
        Extract question and reference_answer items from rubric entries.
        """
        combined_qa = []
        
        try:
            # Handle if rubric_items is not a list
            if isinstance(rubric_items, dict):
                if "questions" in rubric_items:
                    question_items = rubric_items["questions"]
                elif "data" in rubric_items and isinstance(rubric_items["data"], list):
                    question_items = rubric_items["data"]
                elif "items" in rubric_items:
                    question_items = rubric_items["items"]
                else:
                    question_items = [rubric_items]
            elif isinstance(rubric_items, list):
                question_items = rubric_items
            else:
                logger.warning("Invalid rubric_items structure for QA extraction")
                return []
        
            for i, item in enumerate(question_items):
                if not isinstance(item, dict):
                    continue
                
                question = None
                reference_answer = None
                
                # Try different possible keys for questions
                question_keys = [
                    'question', 'q', 'query', 'prompt', 'text', 
                    'question_text', 'question_content', 'problem_statement'
                ]
                for key in question_keys:
                    if key in item and item[key]:
                        question = str(item[key]).strip()
                        break
                
                # Try different possible keys for reference answers
                answer_keys = [
                    'reference_answer', 'answer', 'ref_answer', 'correct_answer', 
                    'solution', 'expected_answer', 'model_answer', 'ideal_answer',
                    'reference_solution', 'sample_answer'
                ]
                for key in answer_keys:
                    if key in item and item[key]:
                        reference_answer = str(item[key]).strip()
                        break
                
                # Only add if both question and reference answer are found
                if question and reference_answer:
                    qa_pair = {
                        "question": question,
                        "reference_answer": reference_answer
                    }
                    
                    # Optionally include additional metadata
                    if 'question_id' in item:
                        qa_pair['question_id'] = item['question_id']
                    if 'marks' in item:
                        qa_pair['marks'] = item['marks']
                    if 'difficulty' in item:
                        qa_pair['difficulty'] = item['difficulty']
                    if 'subject' in item:
                        qa_pair['subject'] = item['subject']
                    
                    combined_qa.append(qa_pair)
                else:
                    logger.debug(f"Skipping item {i}: missing question or reference answer")
            
            logger.info(f"Successfully extracted {len(combined_qa)} QA pairs from {len(question_items)} items")
            
        except Exception as e:
            logger.error(f"Error extracting QA data: {e}")
            return []
        
        return combined_qa

    @classmethod
    def process_rubric_data(cls, input_data: Dict[Any, Any]) -> tuple:
        """
        Process rubric data and extract rubric_json and reference_json
        
        Args:
            input_data: Raw JSON input data
            
        Returns:
            tuple: (rubric_data, reference_data)
        """
        try:
            logger.info("Starting rubric data processing...")
            
            # Extract rubric data
            rubric_data = cls.extract_and_combine_rubric(input_data)
            if not rubric_data:
                logger.warning("No rubric data found in the provided JSON structure")
                # Don't raise error, just return empty data
                return [], []
            
            # Extract reference/QA data from the rubric data
            reference_data = cls.extract_and_combine_qa(rubric_data)
            
            logger.info(f"Processing completed: {len(rubric_data)} rubric items, {len(reference_data)} QA pairs")
            
            return rubric_data, reference_data
            
        except Exception as e:
            logger.error(f"Error processing rubric data: {e}")
            raise ValueError(f"Failed to process rubric data: {str(e)}")