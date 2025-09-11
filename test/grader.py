import os
import json
import pickle
import numpy as np
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Tuple, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RubricGrader:
    def __init__(self, api_key: str, rubric_json_path: str):
        """
        Initialize the RubricGrader with OpenAI API key and rubric file path.
        
        Args:
            api_key (str): OpenAI API key
            rubric_json_path (str): Path to the JSON file containing rubrics
        """
        self.client = OpenAI(api_key=api_key)
        self.rubric_json_path = rubric_json_path
        self.rubrics = []
        self.rubric_embeddings = []
        self.embeddings_file = f"{os.path.splitext(rubric_json_path)[0]}_embeddings.pkl"
        
        # Automatically load rubrics on initialization
        self.load_rubrics()
        
    def load_rubrics(self):
        """
        Load rubrics from the JSON file specified during initialization.
        """
        try:
            with open(self.rubric_json_path, 'r', encoding='utf-8') as f:
                self.rubrics = json.load(f)
            logger.info(f"Loaded {len(self.rubrics)} rubrics from {self.rubric_json_path}")
        except FileNotFoundError:
            logger.error(f"Rubrics file {self.rubric_json_path} not found")
            raise
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON format in {self.rubric_json_path}")
            raise
    
    def create_rubric_text(self, rubric: Dict) -> str:
        """
        Create a comprehensive text representation of a rubric for embedding.
        
        Args:
            rubric (Dict): A single rubric from your format
            
        Returns:
            str: Text representation combining all rubric elements
        """
        text_parts = [
            f"Question: {rubric['question']}",
            f"Key concept: {rubric['criteria']['key_concept']}",
            f"Reference answer: {rubric['reference_answer']}"
        ]
        
        # Add examples
        if 'examples' in rubric['criteria']:
            examples_text = " ".join(rubric['criteria']['examples'])
            text_parts.append(f"Examples: {examples_text}")
        
        # Add additional points
        if 'additional_points' in rubric['criteria']:
            additional_text = " ".join(rubric['criteria']['additional_points'])
            text_parts.append(f"Additional points: {additional_text}")
        
        return " | ".join(text_parts)
    
    def generate_embeddings(self, force_regenerate: bool = False):
        """
        Generate embeddings for all rubrics using OpenAI's embedding model.
        
        Args:
            force_regenerate (bool): If True, regenerate embeddings even if cache exists
        """
        if not force_regenerate and os.path.exists(self.embeddings_file):
            try:
                with open(self.embeddings_file, 'rb') as f:
                    self.rubric_embeddings = pickle.load(f)
                logger.info(f"Loaded cached embeddings from {self.embeddings_file}")
                return
            except Exception as e:
                logger.warning(f"Failed to load cached embeddings: {e}")
        
        if not self.rubrics:
            raise ValueError("No rubrics loaded.")
        
        logger.info("Generating embeddings for rubrics...")
        embeddings = []
        
        for i, rubric in enumerate(self.rubrics):
            rubric_text = self.create_rubric_text(rubric)
            try:
                response = self.client.embeddings.create(
                    input=rubric_text,
                    model="text-embedding-ada-002"
                )
                embeddings.append(response.data[0].embedding)
                logger.info(f"Generated embedding for rubric {i+1}/{len(self.rubrics)}")
            except Exception as e:
                logger.error(f"Failed to generate embedding for rubric {rubric['id']}: {e}")
                raise
        
        self.rubric_embeddings = np.array(embeddings)
        
        # Cache embeddings
        try:
            with open(self.embeddings_file, 'wb') as f:
                pickle.dump(self.rubric_embeddings, f)
            logger.info(f"Cached embeddings to {self.embeddings_file}")
        except Exception as e:
            logger.warning(f"Failed to cache embeddings: {e}")
    
    def find_best_rubric(self, question: str, student_answer: str) -> Tuple[Dict, float]:
        """
        Find the best matching rubric for a question and student answer using cosine similarity.
        
        Args:
            question (str): The question being answered
            student_answer (str): The student's answer to be evaluated
            
        Returns:
            Tuple[Dict, float]: Best matching rubric and similarity score
        """
        if len(self.rubric_embeddings) == 0:
            raise ValueError("No embeddings available. Please call generate_embeddings() first.")
        
        # Create a combined text for better matching
        combined_text = f"Question: {question} | Answer: {student_answer}"
        
        # Generate embedding for combined question and answer
        try:
            response = self.client.embeddings.create(
                input=combined_text,
                model="text-embedding-ada-002"
            )
            answer_embedding = np.array(response.data[0].embedding).reshape(1, -1)
        except Exception as e:
            logger.error(f"Failed to generate embedding for student answer: {e}")
            raise
        
        # Calculate similarities
        similarities = cosine_similarity(answer_embedding, self.rubric_embeddings)[0]
        best_match_index = np.argmax(similarities)
        best_score = similarities[best_match_index]
        best_rubric = self.rubrics[best_match_index]
        
        logger.info(f"Best match: Rubric ID {best_rubric['id']} with similarity {best_score:.3f}")
        return best_rubric, best_score
    
    def grade_answer(self, question: str, student_answer: str, reference_answer: str, rubric: Dict) -> Dict[str, Any]:
        """
        Grade a student answer using OpenAI's LLM based on the provided rubric.
        
        Args:
            question (str): The original question
            student_answer (str): The student's answer
            reference_answer (str): The reference answer from student data
            rubric (Dict): The rubric to use for grading
            
        Returns:
            Dict: Grading results including score, feedback, and details
        """
        max_marks = rubric['marks']
        rubric_question = rubric['question']
        key_concept = rubric['criteria']['key_concept']
        rubric_reference = rubric['reference_answer']
        examples = rubric['criteria'].get('examples', [])
        additional_points = rubric['criteria'].get('additional_points', [])
        
        # Create grading prompt
        prompt = f"""
You are an expert teacher grading student answers. Please evaluate the following student response based on the provided rubric.

QUESTION: {question}

STUDENT ANSWER: {student_answer}

REFERENCE ANSWER (from student data): {reference_answer}

RUBRIC DETAILS:
- Maximum Marks: {max_marks}
- Rubric Question: {rubric_question}
- Key Concept: {key_concept}
- Rubric Reference Answer: {rubric_reference}
- Expected Examples: {', '.join(examples) if examples else 'None specified'}
- Additional Points: {', '.join(additional_points) if additional_points else 'None specified'}

GRADING INSTRUCTIONS:
1. Compare the student answer with both the reference answer and rubric criteria
2. Evaluate how well the student answer demonstrates understanding of the key concept
3. Check if the answer includes relevant examples or points from the rubric
4. Assess accuracy, completeness, and clarity of explanation
5. Consider spelling/grammar but focus primarily on content accuracy
6. Assign a score out of {max_marks} marks

Please provide your evaluation in the following JSON format:
{{
    "score": <numerical score out of {max_marks}>,
    "percentage": <percentage score>,
    "feedback": "<detailed feedback explaining the grade>",
    "strengths": ["<list of strengths in the answer>"],
    "areas_for_improvement": ["<list of areas that could be improved>"],
    "key_concept_understood": <true/false>,
    "examples_included": <number of relevant examples found>,
    "accuracy_assessment": "<High/Medium/Low>",
    "overall_quality": "<Excellent/Good/Satisfactory/Needs Improvement/Poor>"
}}

Provide only the JSON response, no additional text.
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            
            # Parse the JSON response
            result = json.loads(response.choices[0].message.content.strip())
            
            # Add metadata
            result['rubric_id'] = rubric['id']
            result['question'] = question
            result['max_marks'] = max_marks
            result['student_answer'] = student_answer
            result['reference_answer'] = reference_answer
            result['rubric_question'] = rubric_question
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            # Fallback response
            return {
                "score": 0,
                "percentage": 0,
                "feedback": "Error in grading process. Please try again.",
                "error": str(e),
                "rubric_id": rubric['id'],
                "question": question,
                "max_marks": max_marks,
                "student_answer": student_answer,
                "reference_answer": reference_answer
            }
        except Exception as e:
            logger.error(f"Failed to grade answer: {e}")
            raise
    
    def grade_student_submission(self, student_data: Dict[str, str], similarity_threshold: float = 0.3) -> Dict[str, Any]:
        """
        Complete grading pipeline: find best rubric and grade the answer using your student data format.
        
        Args:
            student_data (Dict): Student data in format: 
                {
                    "question": "...",
                    "student_answer": "...", 
                    "reference_answer": "..."
                }
            similarity_threshold (float): Minimum similarity score to accept a rubric match
            
        Returns:
            Dict: Complete grading results
        """
        question = student_data['question']
        student_answer = student_data['student_answer']
        reference_answer = student_data['reference_answer']
        
        # Find the best matching rubric
        best_rubric, similarity_score = self.find_best_rubric(question, student_answer)
        
        if similarity_score < similarity_threshold:
            logger.warning(f"Low similarity score ({similarity_score:.3f}) - rubric match may not be accurate")
        
        # Grade the answer
        grading_result = self.grade_answer(question, student_answer, reference_answer, best_rubric)
        
        # Add similarity information
        grading_result['rubric_similarity'] = similarity_score
        grading_result['similarity_warning'] = similarity_score < similarity_threshold
        
        return grading_result

# Example usage and testing
def main():
    """
    Example usage of the RubricGrader system with your student data format
    """
    # Initialize with your OpenAI API key and rubric file path
      # Replace with your actual API key
    RUBRIC_PATH = "rubrics.json"  # Path to your rubric JSON file
    
    grader = RubricGrader(API_KEY, RUBRIC_PATH)
    
    # Generate embeddings (only needs to be done once, then cached)
    grader.generate_embeddings()
    
    # Example student submission in your format
    student_submission = {
         "question": "List out three ways in which the present life of farmers and herders are different from that of the early people.",
         "student_answer": "sai is a good boy from andhra",
         "reference_answer": "1. Present farmers use advanced machinery whereas early people relied on manual labor. 2. Modern transportation allows easy movement of goods leading to better market access, unlike early subsistence life. 3. Education has improved access to agricultural techniques compared to early life where knowledge was passed down through generations.",
    }
    
    # Grade the submission
    print("--- Grading Student Submission ---")
    print(f"Question: {student_submission['question']}")
    print(f"Student Answer: {student_submission['student_answer']}")
    print(f"Reference Answer: {student_submission['reference_answer']}")
    
    try:
        result = grader.grade_student_submission(student_submission)
        
        print(f"\n=== GRADING RESULTS ===")
        print(f"Matched Rubric ID: {result['rubric_id']}")
        print(f"Rubric Question: {result.get('rubric_question', 'N/A')}")
        print(f"Score: {result['score']}/{result['max_marks']} ({result['percentage']:.1f}%)")
        print(f"Overall Quality: {result.get('overall_quality', 'N/A')}")
        print(f"Accuracy: {result.get('accuracy_assessment', 'N/A')}")
        print(f"Key Concept Understood: {result.get('key_concept_understood', 'N/A')}")
        print(f"Rubric Similarity: {result['rubric_similarity']:.3f}")
        
        if result.get('similarity_warning'):
            print("⚠️  Warning: Low similarity score - rubric match may not be accurate")
        
        print(f"\nFeedback: {result['feedback']}")
        
        if result.get('strengths'):
            print(f"Strengths: {', '.join(result['strengths'])}")
        
        if result.get('areas_for_improvement'):
            print(f"Areas for Improvement: {', '.join(result['areas_for_improvement'])}")
        
    except Exception as e:
        print(f"Error grading submission: {e}")

def grade_multiple_submissions(grader: RubricGrader, submissions: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Helper function to grade multiple student submissions
    
    Args:
        grader (RubricGrader): Initialized grader instance
        submissions (List[Dict]): List of student submissions
        
    Returns:
        List[Dict]: List of grading results
    """
    results = []
    for i, submission in enumerate(submissions, 1):
        print(f"\nGrading submission {i}/{len(submissions)}...")
        try:
            result = grader.grade_student_submission(submission)
            results.append(result)
        except Exception as e:
            print(f"Error grading submission {i}: {e}")
            results.append({"error": str(e), "submission": submission})
    
    return results

if __name__ == "__main__":
    main()