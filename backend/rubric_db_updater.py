#!/usr/bin/env python3
"""
Rubric Database Updater Script
This script processes rubric JSON data and updates the qp_data database table
with rubric_json and reference_json columns.

Usage:
python rubric_db_updater.py --uuid <question_paper_uuid> --roll_no <roll_no> --input <input_json_file>

Requirements:
- requests library: pip install requests
- Your Django server running on localhost:8000 (or modify BASE_URL)
- Input JSON file with rubric data structure
"""

import argparse
import json
import requests
import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional


class RubricProcessor:
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize the Rubric Processor
        
        Args:
            base_url: Base URL of your Django API server
        """
        self.base_url = base_url.rstrip('/')
        self.rubric_api_url = f"{self.base_url}/api/process-rubric-separate/"
        self.qp_data_api_url = f"{self.base_url}/api/qp-data"
        
    def extract_and_combine_rubric(self, input_json: Dict[Any, Any]) -> List[Dict[Any, Any]]:
        """
        Extract rubric_json items from all pages and combine them into a single list.
        """
        combined_rubric = []
        
        try:
            individual_pages = input_json["django_response"]["data"]["rubric_json"]["individual_pages"]
        except KeyError:
            individual_pages = input_json.get("individual_pages", [])
            if not individual_pages:
                try:
                    individual_pages = input_json["rubric_json"]["individual_pages"]
                except:
                    return []
        
        for i, page in enumerate(individual_pages):
            rubric_json = page.get("rubric_json", [])
            for rubric_item in rubric_json:
                combined_rubric.append(rubric_item)
        
        return combined_rubric

    def extract_and_combine_qa(self, input_json: List[Dict[Any, Any]]) -> List[Dict[str, str]]:
        """
        Extract question and reference_answer items from all entries.
        """
        combined_qa = []
        
        try:
            if isinstance(input_json, list):
                question_items = input_json
            elif isinstance(input_json, dict):
                if "questions" in input_json:
                    question_items = input_json["questions"]
                elif "data" in input_json and isinstance(input_json["data"], list):
                    question_items = input_json["data"]
                elif "items" in input_json:
                    question_items = input_json["items"]
                else:
                    question_items = [input_json]
            else:
                return []
        except Exception as e:
            print(f"Error processing QA data: {e}")
            return []
        
        for i, item in enumerate(question_items):
            if not isinstance(item, dict):
                continue
            
            question = None
            reference_answer = None
            
            question_keys = ['question', 'q', 'query', 'prompt', 'text']
            for key in question_keys:
                if key in item:
                    question = item[key]
                    break
            
            answer_keys = ['reference_answer', 'answer', 'ref_answer', 'correct_answer', 'solution', 'expected_answer']
            for key in answer_keys:
                if key in item:
                    reference_answer = item[key]
                    break
            
            if question is not None and reference_answer is not None:
                qa_pair = {
                    "question": question,
                    "reference_answer": reference_answer
                }
                combined_qa.append(qa_pair)
        
        return combined_qa

    def process_rubric_data(self, input_data: Dict[Any, Any]) -> tuple:
        """
        Process rubric data and extract rubric_json and reference_json
        
        Returns:
            tuple: (rubric_data, reference_data)
        """
        print("Processing rubric data...")
        
        # Extract rubric data
        rubric_data = self.extract_and_combine_rubric(input_data)
        if not rubric_data:
            raise ValueError("No rubric data found in the provided JSON structure")
        
        # Extract reference/QA data
        reference_data = self.extract_and_combine_qa(rubric_data)
        
        print(f"Extracted {len(rubric_data)} rubric items and {len(reference_data)} QA pairs")
        
        return rubric_data, reference_data

    def check_qp_data_exists(self, question_paper_uuid: str) -> bool:
        """
        Check if QP data exists for the given UUID
        """
        try:
            response = requests.get(f"{self.qp_data_api_url}/uuid/{question_paper_uuid}/")
            return response.status_code == 200
        except requests.RequestException as e:
            print(f"Error checking QP data existence: {e}")
            return False

    def update_qp_data(self, question_paper_uuid: str, rubric_data: List, reference_data: List) -> bool:
        """
        Update QP data with rubric_json and reference_json
        Works with your existing database structure
        Creates new entry if UUID doesn't exist
        
        Args:
            question_paper_uuid: Question paper UUID
            rubric_data: Processed rubric data
            reference_data: Processed reference/QA data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Prepare the payload for updating QP data
            # Only include fields that exist in your current database
            payload = {
                "question_paper_uuid": question_paper_uuid,
                "rubric_json": rubric_data,
                "reference_json": reference_data
            }
            
            print(f"Processing QP data for UUID: {question_paper_uuid}")
            print(f"Rubric items: {len(rubric_data)}")
            print(f"Reference items: {len(reference_data)}")
            
            # Use your existing process_qp_json endpoint
            response = requests.post(f"{self.qp_data_api_url}/process-qp-json/", json=payload)
            
            if response.status_code in [200, 201]:
                result = response.json()
                action = "Created new" if result.get('created', False) else "Updated existing"
                print(f"✅ Successfully {action.lower()} QP data: {result.get('message', 'Processed')}")
                
                # Print additional info if available
                if 'data' in result:
                    data = result['data']
                    print(f"   - Database ID: {data.get('id', 'N/A')}")
                    print(f"   - Action: {action}")
                    print(f"   - Has Rubric: {data.get('has_rubric_data', 'N/A')}")
                    print(f"   - Has Reference: {data.get('has_reference_data', 'N/A')}")
                
                return True
            else:
                print(f"❌ Failed to update QP data. Status: {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"Error details: {error_detail}")
                except:
                    print(f"Response: {response.text}")
                return False
                
        except requests.RequestException as e:
            print(f"❌ Network error updating QP data: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error updating QP data: {e}")
            return False

    def process_and_update(self, question_paper_uuid: str, input_file_path: str) -> bool:
        """
        Main method to process rubric data and update database
        
        Args:
            question_paper_uuid: Question paper UUID (will create new entry if doesn't exist)
            input_file_path: Path to input JSON file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Load input JSON file
            print(f"Loading input file: {input_file_path}")
            with open(input_file_path, 'r', encoding='utf-8') as f:
                input_data = json.load(f)
            
            # Process rubric data
            rubric_data, reference_data = self.process_rubric_data(input_data)
            
            # Update database
            success = self.update_qp_data(question_paper_uuid, rubric_data, reference_data)
            
            if success:
                print("Process completed successfully!")
                
                # Optionally save processed data to files for verification
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                rubric_file = f"processed_rubric_synthesizer_{question_paper_uuid}_{timestamp}.json"
                reference_file = f"processed_rubric_reference_{question_paper_uuid}_{timestamp}.json"
                
                with open(rubric_file, 'w', encoding='utf-8') as f:
                    json.dump(rubric_data, f, indent=2, ensure_ascii=False)
                
                with open(reference_file, 'w', encoding='utf-8') as f:
                    json.dump(reference_data, f, indent=2, ensure_ascii=False)
                
                print(f"Processed files saved for verification:")
                print(f"   - {rubric_file}")
                print(f"   - {reference_file}")
                
            return success
            
        except FileNotFoundError:
            print(f"Input file not found: {input_file_path}")
            return False
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in input file: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description='Process rubric JSON and update database')
    parser.add_argument('--uuid', required=True, help='Question Paper UUID (will create new entry if doesn\'t exist)')
    parser.add_argument('--input', required=True, help='Input JSON file path')
    parser.add_argument('--base_url', default='http://localhost:8000', help='Django API base URL')
    
    args = parser.parse_args()
    
    # Validate input file exists
    if not os.path.exists(args.input):
        print(f"Input file does not exist: {args.input}")
        sys.exit(1)
    
    print("Starting Rubric Database Updater")
    print(f"UUID: {args.uuid}")
    print(f"Input File: {args.input}")
    print(f"API Base URL: {args.base_url}")
    print("-" * 50)
    
    # Create processor instance
    processor = RubricProcessor(base_url=args.base_url)
    
    # Process and update
    success = processor.process_and_update(args.uuid, args.input)
    
    if success:
        print("\nScript completed successfully!")
        sys.exit(0)
    else:
        print("\nScript failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()