import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class PipelineAPIClient:
    def __init__(self):
        self.api_urls = {
            'stamps': "http://localhost:5000/process-stamps", #can change this to global url later
            'ocr': "http://localhost:5001/ocr/roll", #can change this to global url later
            'chunking': "http://localhost:5002/process-ocr-chunks", #can change this to global url later
            'qa': "http://127.0.0.1:5003/api/qa-mapping", #can change this to global url later
            'grading': "http://localhost:5007/grade" #can change this to global url later
        }
        
        self.timeout = 300  # 5 minutes
        self.session = requests.Session()
        self.session.timeout = self.timeout
    
    def process_ocr(self, roll_no, question_paper_uuid):
        """Call OCR API"""
        try:
            url = f"{self.api_urls['ocr']}/{roll_no}/uuid/{question_paper_uuid}"
            payload = {
                "word_level": False,
                "process_all": True,
                "include_metadata": True
            }
            
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            return {"success": True, "data": response.json()}
            
        except Exception as e:
            logger.error(f"OCR API failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def process_chunking(self, roll_no, question_paper_uuid):
        """Call Chunking API"""
        try:
            url = self.api_urls['chunking']
            payload = {
                "question_paper_uuid": question_paper_uuid,
                "roll_no": roll_no,
                "openai_api_key": getattr(settings, 'OPENAI_API_KEY', ''),
                "max_chunk_size": 1500
            }
            
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            return {"success": True, "data": response.json()}
            
        except Exception as e:
            logger.error(f"Chunking API failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def process_qa_mapping(self, roll_no, question_paper_uuid):
        """Call QA Mapping API"""
        try:
            url = self.api_urls['qa']
            payload = {
                "roll_no": roll_no,
                "question_paper_uuid": question_paper_uuid,
                "top_k": 3
            }
            
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            return {"success": True, "data": response.json()}
            
        except Exception as e:
            logger.error(f"QA API failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def process_grading(self, roll_no, question_paper_uuid):
        """Call Grading API"""
        try:
            url = self.api_urls['grading']
            payload = {
                "roll_no": roll_no,
                "question_paper_uuid": question_paper_uuid,
                "grading_type": "Very Liberal"
            }
            
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            return {"success": True, "data": response.json()}
            
        except Exception as e:
            logger.error(f"Grading API failed: {str(e)}")
            return {"success": False, "error": str(e)}