from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
import os
import json
import numpy as np
from numpy.linalg import norm
import requests
import logging
from datetime import datetime
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration

DATABASE_URL = "https://transback.transpoze.ai/api"

# Webhook Configuration
WEBHOOK_URL = "https://transback.transpoze.ai/api/qa-data/process-qa-json/"
WEBHOOK_TIMEOUT = 30
WEBHOOK_MAX_RETRIES = 3

class QAProcessor:
    def __init__(self):
        self.reference_questions = []  # Will be loaded from database
    
    def fetch_reference_questions_from_db(self, question_paper_uuid):
        """Fetch reference questions from Django database API"""
        try:
            url = f"{DATABASE_URL}/qp-data/uuid/{question_paper_uuid}/"
            
            logger.info(f"Fetching reference questions from: {url}")
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"API Response structure: {list(data.keys())}")
                
                if data.get('success', False):
                    # Extract reference_json from the nested structure
                    qp_data = data.get('data', {})
                    reference_json = qp_data.get('reference_json', [])
                    
                    if not reference_json:
                        logger.error("No reference_json found in QP data")
                        return None
                    
                    logger.info(f"Successfully fetched {len(reference_json)} reference questions")
                    
                    # Validate the structure of reference questions
                    valid_questions = []
                    for i, ref in enumerate(reference_json):
                        if isinstance(ref, dict) and 'question' in ref and 'reference_answer' in ref:
                            valid_questions.append(ref)
                        else:
                            logger.warning(f"Invalid reference question structure at index {i}: {ref}")
                    
                    logger.info(f"Validated {len(valid_questions)} reference questions")
                    return valid_questions
                else:
                    logger.error(f"API returned success=False: {data}")
                    return None
            else:
                logger.error(f"HTTP Error {response.status_code}: {response.text}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Network error while fetching reference questions: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing reference questions response: {e}")
            return None
    
    def load_reference_questions(self, question_paper_uuid):
        """Load reference questions from database"""
        reference_questions = self.fetch_reference_questions_from_db(question_paper_uuid)
        
        if reference_questions:
            self.reference_questions = reference_questions
            logger.info(f"Loaded {len(self.reference_questions)} reference questions from database")
            return True
        else:
            logger.error("Failed to load reference questions from database")
            return False
    
    def fetch_chunk_data_from_db(self, roll_no, question_paper_uuid):
        """Fetch chunk data from Django database API with proper structure handling"""
        try:
            url = f"{DATABASE_URL}/chunk-data/roll/{roll_no}/uuid/{question_paper_uuid}/"
            
            logger.info(f"Fetching data from: {url}")
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"API Response structure: {list(data.keys())}")
                
                if data.get('success', False):
                    # Handle the nested structure properly
                    chunk_data = data.get('data', {}).get('chunk_data', {})
                    
                    # Log the structure for debugging
                    logger.info(f"Chunk data keys: {list(chunk_data.keys())}")
                    
                    # Extract chunks from the nested structure
                    chunks = chunk_data.get('chunks', [])
                    
                    if not chunks:
                        logger.error("No chunks found in chunk_data")
                        return None
                    
                    logger.info(f"Successfully extracted {len(chunks)} chunks")
                    
                    # Return the chunks in the expected format
                    return {
                        'chunks': chunks,
                        'total_chunks': len(chunks),
                        'roll_no': chunk_data.get('roll_no', roll_no),
                        'question_paper_uuid': chunk_data.get('question_paper_uuid', question_paper_uuid),
                        'page_info': chunk_data.get('page_info', []),
                        'total_pages': chunk_data.get('total_pages', 0)
                    }
                else:
                    logger.error(f"API returned success=False: {data}")
                    return None
            else:
                logger.error(f"HTTP Error {response.status_code}: {response.text}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Network error while fetching chunk data: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing chunk data response: {e}")
            return None
    
    def get_embedding(self, text, model="text-embedding-ada-002"):
        """Generate OpenAI embedding for text with better error handling"""
        try:
            # Clean the text before embedding
            clean_text = text.strip()
            if not clean_text:
                logger.warning("Empty text provided for embedding")
                return None
            
            # Truncate text if it's too long (OpenAI has token limits)
            if len(clean_text) > 8000:  # Conservative limit
                clean_text = clean_text[:8000]
                logger.warning(f"Text truncated to 8000 characters")
            
            response = openai.embeddings.create(
                input=clean_text,
                model=model
            )
            
            embedding = response.data[0].embedding
            
            # Ensure embedding is a list of Python floats
            embedding = [float(x) for x in embedding]
            
            logger.debug(f"Generated embedding of length {len(embedding)}")
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            logger.error(f"Text length: {len(text) if text else 'None'}")
            logger.error(f"Text preview: {text[:100] if text else 'None'}...")
            raise
    
    def cosine_similarity(self, a, b):
        """Calculate cosine similarity between two vectors with better error handling"""
        if a is None or b is None:
            logger.warning("One or both embeddings are None")
            return 0.0
        
        try:
            # Convert to numpy arrays if they aren't already
            a = np.array(a)
            b = np.array(b)
            
            # Calculate norms
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            # Check for zero vectors
            if norm_a == 0 or norm_b == 0:
                logger.warning("One or both vectors have zero norm")
                return 0.0
            
            # Calculate cosine similarity
            similarity = np.dot(a, b) / (norm_a * norm_b)
            
            # Ensure the result is a Python float
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    def find_best_chunks_for_question(self, question_index, chunk_embeddings, reference_embeddings, chunks, top_k=2):
        """Find best matching chunks for a reference question"""
        ref_emb = reference_embeddings[question_index]
        if ref_emb is None:
            logger.warning(f"No embedding for reference question {question_index}")
            return []
            
        sims = []
        for j, chunk_emb in enumerate(chunk_embeddings):
            if chunk_emb is not None:
                sim_score = self.cosine_similarity(ref_emb, chunk_emb)
                # Ensure both j and sim_score are Python native types
                sims.append((int(j), float(sim_score)))
            else:
                logger.warning(f"No embedding for chunk {j}")
                
        # Sort by similarity score (descending)
        sims = sorted(sims, key=lambda x: x[1], reverse=True)
        
        # Get top k results
        # Get top k results - ensure top_k is an integer
        k = int(top_k) if top_k is not None else 2
        top_chunks = sims[:k]
        
        # Sort by original chunk index to maintain order
        top_chunks = sorted(top_chunks, key=lambda x: x[0])
        
        # Log for debugging
        logger.info(f"Question {question_index + 1}: Found {len(top_chunks)} matching chunks")
        for idx, score in top_chunks:
            logger.info(f"  Chunk {idx}: similarity={score:.4f}")
        
        return top_chunks
    
    def clean_chunk_text(self, chunk_text):
        """Clean and preprocess chunk text"""
        if not chunk_text:
            return ""
        
        # Remove excessive whitespace and clean up text
        cleaned = ' '.join(chunk_text.split())
        return cleaned
    
    def generate_qa_mapping(self, question, reference_answer, student_chunks_text):
        """Generate QA mapping using OpenAI with improved prompt"""
        # Clean the student chunks text
        cleaned_chunks = self.clean_chunk_text(student_chunks_text)
        
        prompt = f"""
You are given:
1. A question
2. The reference answer for that question  
3. The student's raw answer text (may contain extra unrelated content)

Your task:
- Search through ALL provided text carefully.
- Identify every line, label, numbering, or sentence that is part of the student's answer to the given question.
- Include ALL parts in their original order, without skipping anything that belongs to the answer.
- Do NOT correct spelling, grammar, or formatting.
- Do NOT summarize or paraphrase.
- Do NOT remove numbering or labels (e.g., "A)", "1)", "i)").
- If answer parts are non-contiguous in the text, combine them in the original order found.
- Also match the answer by detecting question numbering or labels (e.g., if the question is "3(a)", "Q3", "Question 3", "3."), and extract all text that follows that numbering as part of the student's answer until the next question's numbering or clear separation.
- If no relevant answer is found, return "NO_ANSWER_FOUND" as the student_answer.

Question:
"{question}"

Reference Answer:
"{reference_answer}"

Student Text:
"{cleaned_chunks}"

Output format:
{{
    "question": "the exact question text",
    "reference_answer": "the reference answer", 
    "student_answer": "the extracted student answer text"
}}

Output JSON ONLY, nothing else.
"""

        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a precise assistant that extracts student answers based on the reference answer. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=1000
            )

            answer_text = response.choices[0].message.content.strip()
            
            # Remove surrounding backticks if present
            if answer_text.startswith("```json"):
                answer_text = "\n".join(answer_text.split("\n")[1:-1])
            elif answer_text.startswith("```"):
                answer_text = "\n".join(answer_text.split("\n")[1:-1])
            
            logger.info(f"GPT Response: {answer_text[:200]}...")

            qa_pair = json.loads(answer_text)
            
            # Validate the response structure
            if not all(key in qa_pair for key in ["question", "reference_answer", "student_answer"]):
                logger.error("Invalid QA pair structure returned from GPT")
                return {
                    "question": question,
                    "reference_answer": reference_answer,
                    "student_answer": "INVALID_RESPONSE_STRUCTURE"
                }
            
            return qa_pair
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON for question: {question[:50]}... Error: {e}")
            return {
                "question": question,
                "reference_answer": reference_answer,
                "student_answer": "PARSING_ERROR"
            }
        except Exception as e:
            logger.error(f"Error generating QA mapping: {e}")
            return {
                "question": question,
                "reference_answer": reference_answer,
                "student_answer": "GENERATION_ERROR"
            }
    
    def process_all_questions(self, chunk_embeddings, reference_embeddings, chunks, top_k=3):
        """Process all questions and generate complete QA mapping"""
        all_qa_pairs = []

        logger.info(f"Processing {len(self.reference_questions)} questions...")

        for question_index in range(len(self.reference_questions)):
            logger.info(f"Processing question {question_index + 1}/{len(self.reference_questions)}")

            try:
                # Find best chunks for this question
                top_chunks = self.find_best_chunks_for_question(
                    question_index, chunk_embeddings, reference_embeddings,
                    chunks, top_k=top_k
                )

                if not top_chunks:
                    logger.warning(f"No chunks found for question {question_index + 1}")
                    all_qa_pairs.append({
                        "question": self.reference_questions[question_index]['question'],
                        "reference_answer": self.reference_questions[question_index]['reference_answer'],
                        "student_answer": "NO_CHUNKS_FOUND"
                    })
                    continue

                # Concatenate chunk texts with better error handling
                student_chunks_text_parts = []
                for chunk_idx, similarity_score in top_chunks:
                    try:
                        # Ensure chunk_idx is a valid integer
                        chunk_idx = int(chunk_idx)
                        
                        # Validate index bounds
                        if 0 <= chunk_idx < len(chunks):
                            chunk_text = chunks[chunk_idx].get('chunk_text', '')
                            if chunk_text and chunk_text.strip():
                                student_chunks_text_parts.append(chunk_text.strip())
                                logger.info(f"  Added chunk {chunk_idx} (similarity: {similarity_score:.4f})")
                            else:
                                logger.warning(f"  Empty chunk text at index {chunk_idx}")
                        else:
                            logger.error(f"  Invalid chunk index: {chunk_idx} (max: {len(chunks)-1})")
                            
                    except (ValueError, TypeError) as e:
                        logger.error(f"  Error processing chunk index {chunk_idx}: {e}")
                        continue
                
                # Join all valid chunk texts
                student_chunks_text = " ".join(student_chunks_text_parts)
                
                if not student_chunks_text.strip():
                    logger.warning(f"Empty chunk text for question {question_index + 1}")
                    all_qa_pairs.append({
                        "question": self.reference_questions[question_index]['question'],
                        "reference_answer": self.reference_questions[question_index]['reference_answer'],
                        "student_answer": "EMPTY_CHUNKS"
                    })
                    continue

                question = self.reference_questions[question_index]['question']
                reference_answer = self.reference_questions[question_index]['reference_answer']

                logger.info(f"Processing chunks for question: {question[:50]}...")
                logger.info(f"Chunk text length: {len(student_chunks_text)} characters")
                logger.info(f"Using {len(student_chunks_text_parts)} chunks for processing")

                # Generate QA mapping for this question
                qa_mapping = self.generate_qa_mapping(question, reference_answer, student_chunks_text)

                if qa_mapping:
                    all_qa_pairs.append(qa_mapping)
                else:
                    # Fallback if mapping fails
                    all_qa_pairs.append({
                        "question": question,
                        "reference_answer": reference_answer,
                        "student_answer": "EXTRACTION_FAILED"
                    })

            except Exception as e:
                logger.error(f"Error processing question {question_index + 1}: {e}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
                
                all_qa_pairs.append({
                    "question": self.reference_questions[question_index]['question'],
                    "reference_answer": self.reference_questions[question_index]['reference_answer'],
                    "student_answer": f"PROCESSING_ERROR: {str(e)}"
                })

        return all_qa_pairs

def send_webhook_notification(webhook_url: str, data: dict, max_retries: int = 3) -> bool:
    """Send QA results to webhook URL with retry logic and debugging"""
    
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'QA-Mapping-API/1.0'
    }
    
    # DEBUG: Log the webhook payload size and structure
    print(f"🐛 DEBUG: QA Webhook payload size: {len(str(data))} characters")
    print(f"🐛 DEBUG: QA Webhook payload keys: {list(data.keys())}")
    if 'total_questions_processed' in data.get('data', {}):
        print(f"🐛 DEBUG: Total QA pairs being sent: {data['data']['total_questions_processed']}")
    
    for attempt in range(max_retries):
        try:
            print(f"📤 Sending QA webhook notification (attempt {attempt + 1}/{max_retries})")
            print(f"🎯 QA Webhook URL: {webhook_url}")
            
            # DEBUG: Log request details
            print(f"🐛 DEBUG: Request headers: {headers}")
            print(f"🐛 DEBUG: Request timeout: {WEBHOOK_TIMEOUT} seconds")
            
            response = requests.post(
                webhook_url, 
                json=data, 
                headers=headers,
                timeout=WEBHOOK_TIMEOUT
            )
            
            print(f"📊 QA Webhook response status: {response.status_code}")
            
            # DEBUG: Enhanced response logging
            print(f"🐛 DEBUG: Response headers: {dict(response.headers)}")
            print(f"🐛 DEBUG: Response time: {response.elapsed.total_seconds():.2f} seconds")
            
            if response.status_code in [200, 201, 202]:
                print("✅ QA Webhook notification sent successfully")
                print(f"🐛 DEBUG: Success response body: {response.text[:500]}...")  # First 500 chars
                return True
            else:
                print(f"⚠️ QA Webhook returned non-success status: {response.status_code}")
                print(f"🐛 DEBUG: Error response body: {response.text}")
                print(f"🐛 DEBUG: Response content type: {response.headers.get('content-type', 'unknown')}")
                
        except requests.exceptions.Timeout:
            print(f"⏰ QA Webhook timeout on attempt {attempt + 1}")
            print(f"🐛 DEBUG: Timeout occurred after {WEBHOOK_TIMEOUT} seconds")
        except requests.exceptions.ConnectionError as e:
            print(f"🔌 QA Webhook connection error on attempt {attempt + 1}: {str(e)}")
            print(f"🐛 DEBUG: Connection error details: {type(e).__name__}")
        except requests.exceptions.RequestException as e:
            print(f"❌ QA Webhook request error on attempt {attempt + 1}: {str(e)}")
            print(f"🐛 DEBUG: Request exception type: {type(e).__name__}")
            print(f"🐛 DEBUG: Request exception details: {repr(e)}")
        except Exception as e:
            print(f"❌ Unexpected QA webhook error on attempt {attempt + 1}: {str(e)}")
            print(f"🐛 DEBUG: Unexpected error type: {type(e).__name__}")
            import traceback
            print(f"🐛 DEBUG: Full traceback:\n{traceback.format_exc()}")
        
        if attempt < max_retries - 1:
            print(f"🔄 Retrying QA webhook in 2 seconds...")
            time.sleep(2)
    
    print("❌ Failed to send QA webhook notification after all retries")
    return False

def validate_webhook_url(url: str) -> bool:
    """Validate webhook URL format and accessibility"""
    try:
        print(f"🐛 DEBUG: Validating QA webhook URL: {url}")
        
        # Basic URL format validation
        if not url.startswith(('http://', 'https://')):
            print(f"🐛 DEBUG: Invalid URL scheme: {url}")
            return False
        
        # Test basic connectivity with HEAD request
        response = requests.head(url, timeout=10)
        print(f"🐛 DEBUG: HEAD request status: {response.status_code}")
        print(f"🐛 DEBUG: Server headers: {dict(response.headers)}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"🐛 DEBUG: QA URL validation failed: {str(e)}")
        return False
    except Exception as e:
        print(f"🐛 DEBUG: Unexpected QA validation error: {str(e)}")
        return False

# Initialize QA processor
qa_processor = QAProcessor()

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "message": "QA Mapping API with Database Reference JSON is running",
        "timestamp": datetime.now().isoformat(),
        "database_url": DATABASE_URL,
        "webhook_url": WEBHOOK_URL,
        "webhook_configured": WEBHOOK_URL is not None,
        "features": ["QA Processing", "Semantic Matching", "OpenAI Integration", "Webhook Notifications", "Database Reference JSON"],
        "database_structure": "Updated for nested chunk_data structure and reference_json fetching"
    }), 200

@app.route('/api/qa-mapping', methods=['POST'])
def process_qa_mapping():
    """Main endpoint for QA mapping processing with webhook notification"""
    try:
        # Get JSON data from request
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        # Extract required parameters
        roll_no = data.get('roll_no')
        question_paper_uuid = data.get('question_paper_uuid')
        top_k = data.get('top_k', 3)  # Default to 3 if not provided
        
        if not roll_no or not question_paper_uuid:
            return jsonify({
                "success": False,
                "error": "Missing required parameters: roll_no and question_paper_uuid"
            }), 400
        
        logger.info(f"Processing QA for Roll No: {roll_no}, Question Paper UUID: {question_paper_uuid}")
        
        # Load reference questions from database first
        logger.info("Loading reference questions from database...")
        reference_loaded = qa_processor.load_reference_questions(question_paper_uuid)
        
        if not reference_loaded:
            return jsonify({
                "success": False,
                "error": "Failed to load reference questions from database"
            }), 404
        
        # Fetch chunk data from database
        logger.info("Fetching chunk data from database...")
        chunk_data = qa_processor.fetch_chunk_data_from_db(roll_no, question_paper_uuid)
        
        if not chunk_data:
            return jsonify({
                "success": False,
                "error": "Failed to fetch chunk data from database"
            }), 404
        
        # Extract chunks from the fetched data
        chunks = chunk_data.get('chunks', [])
        if not chunks:
            return jsonify({
                "success": False,
                "error": "No chunks found in the fetched data"
            }), 404
        
        logger.info(f"Successfully loaded {len(chunks)} chunks from database")
        
        # Validate chunks structure
        valid_chunks = 0
        for i, chunk in enumerate(chunks):
            if isinstance(chunk, dict) and chunk.get('chunk_text'):
                valid_chunks += 1
            else:
                logger.warning(f"Invalid chunk structure at index {i}: {type(chunk)}")
        
        logger.info(f"Found {valid_chunks} valid chunks out of {len(chunks)} total")
        
        # Generate embeddings for chunks
        logger.info("Generating embeddings for chunks...")
        chunk_embeddings = []
        embedding_errors = 0
        
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}: {chunk.get('chunk_id', 'Unknown')}")
            
            try:
                chunk_text = chunk.get('chunk_text', '')
                if chunk_text and chunk_text.strip():
                    logger.debug(f"Chunk {i} text length: {len(chunk_text)}")
                    emb = qa_processor.get_embedding(chunk_text)
                    chunk_embeddings.append(emb)
                    
                    if emb is not None:
                        logger.debug(f"Successfully embedded chunk {i}")
                    else:
                        logger.warning(f"Failed to embed chunk {i}")
                        embedding_errors += 1
                else:
                    logger.warning(f"Empty chunk text for chunk {i+1}")
                    chunk_embeddings.append(None)
                    embedding_errors += 1
                    
            except Exception as e:
                logger.error(f"Error processing chunk {i}: {e}")
                chunk_embeddings.append(None)
                embedding_errors += 1
                
        successful_embeddings = len([e for e in chunk_embeddings if e is not None])
        logger.info(f"Generated embeddings for {successful_embeddings} chunks ({embedding_errors} errors)")
        
        if successful_embeddings == 0:
            return jsonify({
                "success": False,
                "error": "Failed to generate any chunk embeddings"
            }), 500
        
        # Generate embeddings for reference answers
        logger.info("Generating embeddings for reference answers...")
        reference_embeddings = []
        ref_embedding_errors = 0
        
        for i, ref in enumerate(qa_processor.reference_questions):
            logger.info(f"Processing reference {i+1}/{len(qa_processor.reference_questions)}")
            
            try:
                ref_text = ref['reference_answer']
                logger.debug(f"Reference {i} text: {ref_text[:50]}...")
                
                emb = qa_processor.get_embedding(ref_text)
                reference_embeddings.append(emb)
                
                if emb is not None:
                    logger.debug(f"Successfully embedded reference {i}")
                else:
                    logger.warning(f"Failed to embed reference {i}")
                    ref_embedding_errors += 1
                    
            except Exception as e:
                logger.error(f"Error processing reference {i}: {e}")
                reference_embeddings.append(None)
                ref_embedding_errors += 1
                
        successful_ref_embeddings = len([e for e in reference_embeddings if e is not None])
        logger.info(f"Embedded {successful_ref_embeddings} reference answers ({ref_embedding_errors} errors)")
        
        if successful_ref_embeddings == 0:
            return jsonify({
                "success": False,
                "error": "Failed to generate any reference embeddings"
            }), 500
        
        # Validate data before processing
        logger.info("Validating data before QA processing...")
        logger.info(f"Chunks: {len(chunks)}, Chunk embeddings: {len(chunk_embeddings)}")
        logger.info(f"Reference questions: {len(qa_processor.reference_questions)}, Reference embeddings: {len(reference_embeddings)}")
        logger.info(f"Top-k value: {top_k}")
        
        # Process all questions
        logger.info("Starting complete QA processing...")
        complete_qa_mapping = qa_processor.process_all_questions(
            chunk_embeddings, reference_embeddings, chunks, top_k=top_k
        )
        
        logger.info(f"Successfully processed {len(complete_qa_mapping)} questions")
        
        # Validate QA mapping results
        successful_extractions = sum(1 for qa in complete_qa_mapping 
                                   if qa.get('student_answer') and 
                                   not qa.get('student_answer', '').startswith(('NO_', 'EMPTY_', 'EXTRACTION_', 'PROCESSING_', 'PARSING_', 'GENERATION_')))
        
        logger.info(f"Successfully extracted answers for {successful_extractions}/{len(complete_qa_mapping)} questions")
        
        # Prepare response data
        response_data = {
            "success": True,
            "data": {
                "roll_no": roll_no,
                "question_paper_uuid": question_paper_uuid,
                "total_questions_processed": len(complete_qa_mapping),
                "successful_extractions": successful_extractions,
                "qa_mapping": complete_qa_mapping,
                "processing_timestamp": datetime.now().isoformat(),
                "processing_summary": {
                    "status": "completed",
                    "chunks_processed": len(chunks),
                    "valid_chunks": valid_chunks,
                    "chunk_embeddings_generated": successful_embeddings,
                    "chunk_embedding_errors": embedding_errors,
                    "reference_embeddings_generated": successful_ref_embeddings,
                    "reference_embedding_errors": ref_embedding_errors,
                    "reference_questions_loaded": len(qa_processor.reference_questions),
                    "top_k_used": top_k,
                    "total_pages": chunk_data.get('total_pages', 0)
                }
            }
        }

        # DEBUG: Validate webhook URL before sending
        print(f"🐛 DEBUG: Starting QA webhook notification process")
        print(f"🐛 DEBUG: QA Webhook URL to test: {WEBHOOK_URL}")

        if WEBHOOK_URL:
            url_valid = validate_webhook_url(WEBHOOK_URL)
            print(f"🐛 DEBUG: QA Webhook URL validation result: {url_valid}")

            # DEBUG: Log payload summary before sending
            payload_summary = {
                'roll_no': response_data['data'].get('roll_no'),
                'question_paper_uuid': response_data['data'].get('question_paper_uuid'),
                'total_questions_processed': response_data['data'].get('total_questions_processed'),
                'successful_extractions': response_data['data'].get('successful_extractions'),
                'status': response_data['data'].get('processing_summary', {}).get('status')
            }
            print(f"🐛 DEBUG: QA Payload summary: {payload_summary}")

            # Send webhook notification
            if url_valid:
                print("📤 Attempting to send QA webhook notification...")
                webhook_success = send_webhook_notification(WEBHOOK_URL, response_data, WEBHOOK_MAX_RETRIES)
                
                if webhook_success:
                    print("✅ QA Webhook notification sent successfully")
                    response_data['webhook_status'] = 'sent'
                else:
                    print("❌ Failed to send QA webhook notification")
                    response_data['webhook_status'] = 'failed'
            else:
                print("⚠️ QA Webhook URL validation failed, skipping notification")
                response_data['webhook_status'] = 'skipped_invalid_url'
        else:
            print("⚠️ No QA Webhook URL configured")
            response_data['webhook_status'] = 'not_configured'
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error processing QA mapping: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}",
            "traceback": traceback.format_exc() if app.debug else None
        }), 500

@app.route('/api/reference-questions/<question_paper_uuid>', methods=['GET'])
def get_reference_questions(question_paper_uuid):
    """Get reference questions for a specific question paper UUID"""
    try:
        # Load reference questions from database
        reference_loaded = qa_processor.load_reference_questions(question_paper_uuid)
        
        if not reference_loaded:
            return jsonify({
                "success": False,
                "error": "Failed to load reference questions from database"
            }), 404
        
        return jsonify({
            "success": True,
            "data": {
                "question_paper_uuid": question_paper_uuid,
                "total_questions": len(qa_processor.reference_questions),
                "reference_questions": qa_processor.reference_questions
            }
        }), 200
    except Exception as e:
        logger.error(f"Error fetching reference questions: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500

@app.route('/api/qa-mapping/<roll_no>/<question_paper_uuid>', methods=['GET'])
def process_qa_mapping_get(roll_no, question_paper_uuid):
    """GET endpoint for QA mapping processing (alternative to POST)"""
    try:
        top_k = request.args.get('top_k', 3, type=int)
        
        logger.info(f"Processing QA for Roll No: {roll_no}, Question Paper UUID: {question_paper_uuid}")
        
        # Load reference questions from database first
        logger.info("Loading reference questions from database...")
        reference_loaded = qa_processor.load_reference_questions(question_paper_uuid)
        
        if not reference_loaded:
            return jsonify({
                "success": False,
                "error": "Failed to load reference questions from database"
            }), 404
        
        # Fetch chunk data from database
        chunk_data = qa_processor.fetch_chunk_data_from_db(roll_no, question_paper_uuid)
        
        if not chunk_data:
            return jsonify({
                "success": False,
                "error": "Failed to fetch chunk data from database"
            }), 404
        
        chunks = chunk_data.get('chunks', [])
        if not chunks:
            return jsonify({
                "success": False,
                "error": "No chunks found in the fetched data"
            }), 404
        
        # Generate embeddings for chunks
        logger.info("Generating embeddings for chunks...")
        chunk_embeddings = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")
            chunk_text = chunk.get('chunk_text', '')
            if chunk_text.strip():
                emb = qa_processor.get_embedding(chunk_text)
                chunk_embeddings.append(emb)
            else:
                chunk_embeddings.append(None)
        
        # Generate embeddings for reference answers
        logger.info("Generating embeddings for reference answers...")
        reference_embeddings = []
        for i, ref in enumerate(qa_processor.reference_questions):
            logger.info(f"Processing reference {i+1}/{len(qa_processor.reference_questions)}")
            emb = qa_processor.get_embedding(ref['reference_answer'])
            reference_embeddings.append(emb)
        
        # Process all questions
        logger.info("Starting complete QA processing...")
        complete_qa_mapping = qa_processor.process_all_questions(
            chunk_embeddings, reference_embeddings, chunks, top_k=top_k
        )
        
        logger.info(f"Successfully processed {len(complete_qa_mapping)} questions")
        
        # Prepare response data
        response_data = {
            "success": True,
            "data": {
                "roll_no": roll_no,
                "question_paper_uuid": question_paper_uuid,
                "total_questions_processed": len(complete_qa_mapping),
                "qa_mapping": complete_qa_mapping,
                "processing_timestamp": datetime.now().isoformat(),
                "processing_summary": {
                    "status": "completed",
                    "chunks_processed": len(chunks),
                    "valid_chunks": len([c for c in chunks if c.get('chunk_text', '').strip()]),
                    "embeddings_generated": len([e for e in chunk_embeddings if e is not None]) + len(reference_embeddings),
                    "reference_questions_loaded": len(qa_processor.reference_questions),
                    "top_k_used": top_k,
                    "total_pages": chunk_data.get('total_pages', 0)
                }
            }
        }

        # Send webhook notification for GET requests too
        if WEBHOOK_URL and validate_webhook_url(WEBHOOK_URL):
            print("📤 Attempting to send QA webhook notification (GET request)...")
            webhook_success = send_webhook_notification(WEBHOOK_URL, response_data, WEBHOOK_MAX_RETRIES)
            response_data['webhook_status'] = 'sent' if webhook_success else 'failed'
        else:
            response_data['webhook_status'] = 'skipped'
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error processing QA mapping: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500

@app.route('/test-webhook', methods=['GET', 'POST'])
def test_webhook():
    """Test webhook functionality"""
    try:
        # Test data
        test_data = {
            "success": True,
            "data": {
                "roll_no": "TEST123",
                "question_paper_uuid": "test-uuid-123",
                "total_questions_processed": 2,
                "qa_mapping": [
                    {
                        "question": "Test Question 1",
                        "reference_answer": "Test Reference Answer 1",
                        "student_answer": "Test Student Answer 1"
                    },
                    {
                        "question": "Test Question 2", 
                        "reference_answer": "Test Reference Answer 2",
                        "student_answer": "Test Student Answer 2"
                    }
                ],
                "processing_timestamp": datetime.now().isoformat(),
                "processing_summary": {
                    "status": "completed",
                    "chunks_processed": 5,
                    "valid_chunks": 5,
                    "embeddings_generated": 10,
                    "reference_questions_loaded": 2,
                    "top_k_used": 3,
                    "total_pages": 2
                }
            },
            "test": True
        }

        if not WEBHOOK_URL:
            return jsonify({
                "status": "error",
                "message": "No webhook URL configured"
            }), 400

        # Validate and send webhook
        url_valid = validate_webhook_url(WEBHOOK_URL)
        if not url_valid:
            return jsonify({
                "status": "error", 
                "message": "Webhook URL validation failed",
                "webhook_url": WEBHOOK_URL
            }), 400

        webhook_success = send_webhook_notification(WEBHOOK_URL, test_data, WEBHOOK_MAX_RETRIES)
        
        return jsonify({
            "status": "success" if webhook_success else "error",
            "message": "Webhook test completed",
            "webhook_url": WEBHOOK_URL,
            "webhook_sent": webhook_success,
            "test_data_sent": test_data
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Webhook test failed: {str(e)}",
            "webhook_url": WEBHOOK_URL
        }), 500

@app.route('/webhook-config', methods=['GET'])
def webhook_config():
    """Get webhook configuration"""
    return jsonify({
        "webhook_url": WEBHOOK_URL,
        "webhook_timeout": WEBHOOK_TIMEOUT,
        "webhook_max_retries": WEBHOOK_MAX_RETRIES,
        "webhook_configured": WEBHOOK_URL is not None,
        "url_validation": validate_webhook_url(WEBHOOK_URL) if WEBHOOK_URL else False,
        "database_url": DATABASE_URL,
        "database_structure": "Updated for nested chunk_data structure and reference_json fetching from database"
    })

@app.route('/api/debug/chunk-structure/<roll_no>/<question_paper_uuid>', methods=['GET'])
def debug_chunk_structure(roll_no, question_paper_uuid):
    """Debug endpoint to inspect chunk structure"""
    try:
        # Fetch chunk data from database
        chunk_data = qa_processor.fetch_chunk_data_from_db(roll_no, question_paper_uuid)
        
        if not chunk_data:
            return jsonify({
                "success": False,
                "error": "Failed to fetch chunk data from database"
            }), 404
        
        chunks = chunk_data.get('chunks', [])
        
        # Analyze chunk structure
        structure_analysis = {
            "total_chunks": len(chunks),
            "chunk_keys": list(chunks[0].keys()) if chunks else [],
            "sample_chunk": chunks[0] if chunks else None,
            "chunk_text_lengths": [len(chunk.get('chunk_text', '')) for chunk in chunks],
            "empty_chunks": sum(1 for chunk in chunks if not chunk.get('chunk_text', '').strip()),
            "chunk_ids": [chunk.get('chunk_id', 'No ID') for chunk in chunks],
            "page_info": chunk_data.get('page_info', []),
            "total_pages": chunk_data.get('total_pages', 0)
        }
        
        return jsonify({
            "success": True,
            "data": {
                "roll_no": roll_no,
                "question_paper_uuid": question_paper_uuid,
                "structure_analysis": structure_analysis,
                "raw_chunk_data": chunk_data
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in debug endpoint: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Debug error: {str(e)}"
        }), 500

@app.route('/api/debug/reference-structure/<question_paper_uuid>', methods=['GET'])
def debug_reference_structure(question_paper_uuid):
    """Debug endpoint to inspect reference questions structure"""
    try:
        # Fetch reference questions from database
        reference_questions = qa_processor.fetch_reference_questions_from_db(question_paper_uuid)
        
        if not reference_questions:
            return jsonify({
                "success": False,
                "error": "Failed to fetch reference questions from database"
            }), 404
        
        # Analyze reference structure
        structure_analysis = {
            "total_questions": len(reference_questions),
            "question_keys": list(reference_questions[0].keys()) if reference_questions else [],
            "sample_question": reference_questions[0] if reference_questions else None,
            "marks_distribution": [q.get('marks', 0) for q in reference_questions],
            "questions_with_marks": sum(1 for q in reference_questions if 'marks' in q),
            "questions_with_reference_answer": sum(1 for q in reference_questions if 'reference_answer' in q)
        }
        
        return jsonify({
            "success": True,
            "data": {
                "question_paper_uuid": question_paper_uuid,
                "structure_analysis": structure_analysis,
                "raw_reference_data": reference_questions
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in reference debug endpoint: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Reference debug error: {str(e)}"
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint not found",
        "available_endpoints": [
            "GET / - Health check",
            "POST /api/qa-mapping - Process QA mapping",
            "GET /api/qa-mapping/<roll>/<uuid> - Process QA mapping via GET",
            "GET /api/reference-questions/<uuid> - Get reference questions for specific UUID",
            "GET/POST /test-webhook - Test webhook functionality",
            "GET /webhook-config - Get webhook configuration",
            "GET /api/debug/chunk-structure/<roll>/<uuid> - Debug chunk structure",
            "GET /api/debug/reference-structure/<uuid> - Debug reference questions structure"
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500

@app.errorhandler(405)
def method_not_allowed_error(error):
    return jsonify({
        'success': False,
        'error': 'Method not allowed',
        'message': 'The requested method is not allowed for this endpoint'
    }), 405

@app.errorhandler(400)
def bad_request_error(error):
    return jsonify({
        'success': False,
        'error': 'Bad request',
        'message': 'The request could not be processed due to invalid syntax or missing data'
    }), 400

if __name__ == '__main__':
    # Set debug mode based on environment
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('PORT', 5003))
    host = os.getenv('HOST', '0.0.0.0')
    
    logger.info(f"Starting QA Mapping Flask API with Database Reference JSON on {host}:{port}")
    logger.info(f"Debug mode: {debug_mode}")
    logger.info(f"Database URL: {DATABASE_URL}")
    logger.info(f"Webhook URL: {WEBHOOK_URL}")
    
    # Validate webhook URL on startup
    if WEBHOOK_URL:
        webhook_valid = validate_webhook_url(WEBHOOK_URL)
        print(f"QA Webhook URL validation: {'✅ Valid' if webhook_valid else '❌ Invalid'}")
    else:
        print("WARNING: No QA webhook URL configured")
    
    print("Available endpoints:")
    print("  GET  /                              - Health check")
    print("  POST /api/qa-mapping                - Process QA mapping (with webhook)")
    print("  GET  /api/qa-mapping/<roll>/<uuid>  - Process QA mapping via GET (with webhook)")
    print("  GET  /api/reference-questions/<uuid> - Get reference questions for specific UUID")
    print("  GET/POST /test-webhook              - Test webhook functionality")
    print("  GET  /webhook-config                - Get webhook configuration")
    print("  GET  /api/debug/chunk-structure/<roll>/<uuid> - Debug chunk structure")
    print("  GET  /api/debug/reference-structure/<uuid> - Debug reference questions structure")
    print("\nDatabase Structure Support:")
    print("  ✅ Nested data.chunk_data structure")
    print("  ✅ chunk_id and chunk_text fields")
    print("  ✅ page_info and total_pages support")
    print("  ✅ Enhanced error handling for empty chunks")
    print("  ✅ Reference JSON fetching from database via question_paper_uuid")
    print("  ✅ Dynamic reference questions loading per request")
    
    # Run the Flask app
    app.run(debug=debug_mode, host=host, port=port)