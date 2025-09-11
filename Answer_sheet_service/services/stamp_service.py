import cv2
import os
import shutil
import numpy as np
from PIL import Image
from typing import List, Tuple, Dict, Optional
import base64
import requests
import json
import io
import tempfile
from datetime import datetime
import uuid
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from config import Config

class StampService:
    def __init__(self):
        # Configuration
        self.max_content_length = Config.MAX_CONTENT_LENGTH
        self.temp_folder = Config.TEMP_DIR
        
        # Create necessary directories
        os.makedirs(self.temp_folder, exist_ok=True)
        
        # OpenAI API configuration
        self.openai_api_key = os.environ.get('OPENAI_API_KEY', 'sk-proj-YOUR_ACTUAL_API_KEY_HERE')
        self.openai_api_url = "https://api.openai.com/v1/chat/completions"
        
        # S3 Configuration
        self.s3_bucket_name = Config.S3_BUCKET or "transgrade-answersheet-images"
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client('s3')
            print("✅ S3 client initialized successfully")
        except Exception as e:
            print(f"❌ Error initializing S3 client: {e}")
            self.s3_client = None
        
        # Allowed file extensions
        self.allowed_extensions = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'tif'}
        
        # Default webhook URL - use the stamp-specific webhook URL from config
        self.default_webhook_url = Config.STAMP_WEBHOOK_URL

    def is_openai_configured(self) -> bool:
        """Check if OpenAI API is properly configured"""
        return self.openai_api_key != "sk-proj-YOUR_ACTUAL_API_KEY_HERE"
    
    def is_s3_configured(self) -> bool:
        """Check if S3 client is available"""
        return self.s3_client is not None
    
    def get_s3_bucket_name(self) -> str:
        """Get S3 bucket name"""
        return self.s3_bucket_name
    
    def get_temp_folder(self) -> str:
        """Get temp folder path"""
        return self.temp_folder
    
    def get_allowed_extensions(self) -> set:
        """Get allowed file extensions"""
        return self.allowed_extensions
    
    def get_default_webhook_url(self) -> str:
        """Get default webhook URL"""
        return self.default_webhook_url

    def allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.allowed_extensions

    # ---------------------------
    # Utility Functions
    # ---------------------------
    def load_and_preprocess(self, path: str, width=1200, do_clahe=False):
        """Load and preprocess image"""
        img = cv2.imread(path)
        if img is None:
            raise FileNotFoundError(path)
        h, w = img.shape[:2]
        if w > width:
            scale = width / w
            img = cv2.resize(img, (width, int(h * scale)), interpolation=cv2.INTER_AREA)
        if do_clahe:
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            cl = clahe.apply(l)
            lab = cv2.merge((cl,a,b))
            img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        return img

    def to_hsv(self, img):
        """Convert BGR to HSV"""
        return cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    def red_mask_from_hsv(self, hsv, s_thresh=80, v_thresh=60):
        """Create red color mask from HSV image"""
        lower1 = np.array([0, s_thresh, v_thresh])
        upper1 = np.array([10, 255, 255])
        lower2 = np.array([170, s_thresh, v_thresh])
        upper2 = np.array([180, 255, 255])
        m1 = cv2.inRange(hsv, lower1, upper1)
        m2 = cv2.inRange(hsv, lower2, upper2)
        mask = cv2.bitwise_or(m1, m2)
        return mask

    def morph_clean(self, mask, img_shape, open_frac=0.003, close_frac=0.01):
        """Apply morphological operations to clean mask"""
        h, w = img_shape[:2]
        k_open = max(3, int(min(h, w) * open_frac))
        k_close = max(3, int(min(h, w) * close_frac))
        k_open = k_open if k_open % 2 == 1 else k_open+1
        k_close = k_close if k_close % 2 == 1 else k_close+1
        kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_open, k_open))
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_close, k_close))
        clean = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open)
        clean = cv2.morphologyEx(clean, cv2.MORPH_CLOSE, kernel_close)
        return clean

    def edges_from_gray(self, gray, low=50, high=150, blur_ksize=5):
        """Extract edges from grayscale image"""
        if blur_ksize > 0:
            gray = cv2.GaussianBlur(gray, (blur_ksize, blur_ksize), 0)
        edges = cv2.Canny(gray, low, high)
        return edges

    def combine_mask_and_edges(self, color_mask, edges, dilate_iter=1):
        """Combine color mask with edges"""
        combined = cv2.bitwise_and(color_mask, edges)
        if dilate_iter > 0:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3))
            combined = cv2.dilate(combined, kernel, iterations=dilate_iter)
        combined = cv2.bitwise_or(combined, color_mask)
        return combined

    def find_contours(self, mask):
        """Find contours in mask"""
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return cnts

    def contour_props(self, cnt, img_area):
        """Calculate contour properties"""
        area = cv2.contourArea(cnt)
        x,y,w,h = cv2.boundingRect(cnt)
        rect = cv2.minAreaRect(cnt)
        box = cv2.boxPoints(rect)
        box = box.astype(int)
        perimeter = cv2.arcLength(cnt, True)
        hull = cv2.convexHull(cnt)
        hull_area = cv2.contourArea(hull) if hull is not None else 0
        solidity = float(area) / hull_area if hull_area > 0 else 0
        aspect = float(w)/h if h>0 else 0
        return dict(area=area, bbox=(x,y,w,h), box=box, rect=rect, perimeter=perimeter,
                    hull_area=hull_area, solidity=solidity, aspect=aspect, area_ratio=area/img_area)

    def filter_contours(self, cnts, img_area, min_area_ratio=0.001, max_area_ratio=0.15,
                        aspect_range=(1.5,4.0), solidity_min=0.4):
        """Filter contours based on properties"""
        candidates = []
        for c in cnts:
            p = self.contour_props(c, img_area)
            if p['area_ratio'] < min_area_ratio or p['area_ratio'] > max_area_ratio:
                continue
            if p['aspect'] < aspect_range[0] or p['aspect'] > aspect_range[1]:
                continue
            if p['solidity'] < solidity_min:
                continue

            x, y, w, h = p['bbox']
            if w < 50 or h < 30:
                continue

            candidates.append((c, p))
        return candidates

    def rotate_crop(self, img, rect):
        """Rotate and crop image based on minimum area rectangle"""
        (cx,cy), (w,h), angle = rect
        if w == 0 or h == 0:
            return None
        angle_correct = angle
        if w < h:
            angle_correct = angle + 90
            w, h = h, w
        M = cv2.getRotationMatrix2D((cx,cy), angle_correct, 1.0)
        h_img, w_img = img.shape[:2]
        rotated = cv2.warpAffine(img, M, (w_img, h_img), flags=cv2.INTER_CUBIC)
        x1 = int(cx - w/2)
        y1 = int(cy - h/2)
        x2 = int(cx + w/2)
        y2 = int(cy + h/2)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w_img, x2), min(h_img, y2)
        crop = rotated[y1:y2, x1:x2].copy()
        return crop

    def orb_match_score(self, imgA, imgB, nfeatures=500):
        """Calculate ORB feature matching score"""
        try:
            orb = cv2.ORB_create(nfeatures)
            kp1, des1 = orb.detectAndCompute(cv2.cvtColor(imgA, cv2.COLOR_BGR2GRAY), None)
            kp2, des2 = orb.detectAndCompute(cv2.cvtColor(imgB, cv2.COLOR_BGR2GRAY), None)
            if des1 is None or des2 is None:
                return 0.0
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            matches = bf.knnMatch(des1, des2, k=2)
            good = []
            for m,n in matches:
                if m.distance < 0.75 * n.distance:
                    good.append(m)
            score = len(good) / max(1, min(len(kp1), len(kp2)))
            return score
        except Exception:
            return 0.0

    def iou(self, boxA, boxB):
        """Calculate Intersection over Union of two boxes"""
        xA1,yA1,wA,hA = boxA
        xA2,yA2 = xA1+wA, yA1+hA
        xB1,yB1,wB,hB = boxB
        xB2,yB2 = xB1+wB, yB1+hB
        xI1 = max(xA1, xB1); yI1 = max(yA1, yB1)
        xI2 = min(xA2, xB2); yI2 = min(yA2, yB2)
        interW = max(0, xI2 - xI1); interH = max(0, yI2 - yI1)
        inter = interW * interH
        areaA = wA*hA; areaB = wB*hB
        union = areaA + areaB - inter
        return inter / union if union>0 else 0

    def nms(self, boxes: List[Tuple[int,int,int,int]], scores: List[float], iou_thresh=0.3):
        """Non-Maximum Suppression"""
        idxs = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        keep = []
        while idxs:
            i = idxs.pop(0)
            keep.append(i)
            idxs = [j for j in idxs if self.iou(boxes[i], boxes[j]) < iou_thresh]
        return keep

    def crop_top_percentage(self, image: np.ndarray, crop_percentage=0.2) -> np.ndarray:
        """Crop the top percentage of an image"""
        h, w = image.shape[:2]
        crop_height = int(h * crop_percentage)
        header_crop = image[0:crop_height, 0:w]
        return header_crop

    # ---------------------------
    # S3 Helper Functions
    # ---------------------------
    def download_image_from_s3(self, s3_key: str, local_path: str) -> bool:
        """Download image from S3 bucket to local path"""
        try:
            if not self.s3_client:
                print("S3 client not available")
                return False
                
            print(f"Downloading s3://{self.s3_bucket_name}/{s3_key} to {local_path}")
            self.s3_client.download_file(self.s3_bucket_name, s3_key, local_path)
            return True
        except ClientError as e:
            print(f"Error downloading {s3_key}: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error downloading {s3_key}: {e}")
            return False

    def fetch_images_from_s3(self, job_id: str) -> List[str]:
        """Fetch all images from S3 for a given job_id and download them locally"""
        try:
            if not self.s3_client:
                raise Exception("S3 client not available")
                
            # Create temp directory for this job
            temp_job_dir = os.path.join(self.temp_folder, job_id)
            os.makedirs(temp_job_dir, exist_ok=True)
            
            # List objects in S3 with the job_id prefix
            prefix = f"{job_id}/"
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                print(f"No files found for job_id: {job_id}")
                return []
            
            local_paths = []
            for obj in response['Contents']:
                s3_key = obj['Key']
                filename = os.path.basename(s3_key)
                
                # Skip if not an image file
                if not self.allowed_file(filename):
                    continue
                    
                local_path = os.path.join(temp_job_dir, filename)
                
                if self.download_image_from_s3(s3_key, local_path):
                    local_paths.append(local_path)
                else:
                    print(f"Failed to download {s3_key}")
            
            # Sort paths to maintain page order
            local_paths.sort()
            print(f"Successfully downloaded {len(local_paths)} images for job {job_id}")
            return local_paths
            
        except Exception as e:
            print(f"Error fetching images for job {job_id}: {e}")
            return []

    # ---------------------------
    # VLM Integration Functions
    # ---------------------------
    def encode_image_to_base64(self, image: np.ndarray) -> str:
        """Convert OpenCV image (BGR) to base64 string for API"""
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        buffer = io.BytesIO()
        pil_image.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    def extract_roll_number_with_vlm(self, image: np.ndarray, image_name: str) -> Optional[str]:
        """Use OpenAI Vision API to extract roll number from stamp image"""
        if not self.is_openai_configured():
            print(f"OpenAI API key not configured for {image_name}")
            return None
            
        try:
            base64_image = self.encode_image_to_base64(image)
            print(f"Analyzing {image_name} with VLM (image size: {image.shape})")

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openai_api_key}"
            }

            payload = {
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """Analyze this image carefully to find a student's roll number or identification number.

Look for:
1. Any text that says "Roll No", "Roll Number", "Student ID", "ID No", "Registration No", etc.
2. Numeric sequences that appear to be student identifiers (usually 4-10 digits)
3. Numbers written in boxes, forms, or answer sheets
4. Any handwritten or printed numbers that could be a student ID

Common formats to look for:
- Simple numbers: 12345, 2023001234
- Numbers with prefixes: S12345, 2023/1234
- Numbers in formats like: 21BCE1234, CSE001, etc.

Please examine the entire image thoroughly. If you find any number that could be a student identifier, respond with ONLY that number (remove any prefixes or special characters, just the digits).

If you cannot find any student identification number, respond with 'NOT_FOUND'.

Examples of good responses: "12345", "2023001234", "1234"
Bad responses: "Student ID: 12345", "Roll No. 12345", explanations"""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 150,
                "temperature": 0.1
            }

            print(f"Sending request to OpenAI for {image_name}...")
            response = requests.post(self.openai_api_url, headers=headers, json=payload, timeout=60)
            
            print(f"OpenAI Response Status: {response.status_code}")
            if response.status_code != 200:
                print(f"OpenAI API Error: {response.text}")
                return None
                
            response.raise_for_status()

            result = response.json()
            if 'choices' not in result or not result['choices']:
                print(f"No choices in OpenAI response: {result}")
                return None
                
            roll_number = result['choices'][0]['message']['content'].strip()
            print(f"VLM Raw Response for {image_name}: '{roll_number}'")

            # Clean up the response
            if roll_number and roll_number != 'NOT_FOUND':
                # Extract only digits from the response
                import re
                digits_only = re.findall(r'\d+', roll_number)
                if digits_only:
                    # Take the longest sequence of digits (most likely to be roll number)
                    final_roll = max(digits_only, key=len)
                    print(f"Extracted roll number: {final_roll}")
                    return final_roll
                else:
                    print(f"No digits found in response: {roll_number}")
                    return None
            else:
                print(f"Roll number not found in {image_name}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"API Request Error for {image_name}: {str(e)}")
            return None
        except KeyError as e:
            print(f"API Response Error for {image_name}: {str(e)}")
            return None
        except Exception as e:
            print(f"Unexpected Error for {image_name}: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None

    # ---------------------------
    # Webhook Functions
    # ---------------------------
    def send_webhook_notification(self, webhook_url: str, data: dict, max_retries: int = 3) -> bool:
        """Send processing results to webhook URL with retry logic"""
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'StampDetectionAPI/1.0'
        }
        
        # DEBUG: Log the webhook payload size and structure
        print(f"🐛 DEBUG: Webhook payload size: {len(str(data))} characters")
        print(f"🐛 DEBUG: Webhook payload keys: {list(data.keys())}")
        if 'processing_summary' in data:
            print(f"🐛 DEBUG: Processing summary: {data['processing_summary']}")
        
        for attempt in range(max_retries):
            try:
                print(f"📤 Sending webhook notification (attempt {attempt + 1}/{max_retries})")
                print(f"🎯 Webhook URL: {webhook_url}")
                
                # DEBUG: Log request details
                print(f"🐛 DEBUG: Request headers: {headers}")
                print(f"🐛 DEBUG: Request timeout: 30 seconds")
                
                response = requests.post(
                    webhook_url, 
                    json=data, 
                    headers=headers,
                    timeout=30
                )
                
                print(f"📊 Webhook response status: {response.status_code}")
                
                # DEBUG: Enhanced response logging
                print(f"🐛 DEBUG: Response headers: {dict(response.headers)}")
                print(f"🐛 DEBUG: Response time: {response.elapsed.total_seconds():.2f} seconds")
                
                if response.status_code in [200, 201, 202]:
                    print("✅ Webhook notification sent successfully")
                    print(f"🐛 DEBUG: Success response body: {response.text[:500]}...")  # First 500 chars
                    return True
                else:
                    print(f"⚠️ Webhook returned non-success status: {response.status_code}")
                    print(f"🐛 DEBUG: Error response body: {response.text}")
                    print(f"🐛 DEBUG: Response content type: {response.headers.get('content-type', 'unknown')}")
                    
            except requests.exceptions.Timeout:
                print(f"⏰ Webhook timeout on attempt {attempt + 1}")
                print(f"🐛 DEBUG: Timeout occurred after 30 seconds")
            except requests.exceptions.ConnectionError as e:
                print(f"🔌 Webhook connection error on attempt {attempt + 1}: {str(e)}")
                print(f"🐛 DEBUG: Connection error details: {type(e).__name__}")
            except requests.exceptions.RequestException as e:
                print(f"❌ Webhook request error on attempt {attempt + 1}: {str(e)}")
                print(f"🐛 DEBUG: Request exception type: {type(e).__name__}")
                print(f"🐛 DEBUG: Request exception details: {repr(e)}")
            except Exception as e:
                print(f"❌ Unexpected webhook error on attempt {attempt + 1}: {str(e)}")
                print(f"🐛 DEBUG: Unexpected error type: {type(e).__name__}")
                import traceback
                print(f"🐛 DEBUG: Full traceback:\n{traceback.format_exc()}")
            
            if attempt < max_retries - 1:
                print(f"🔄 Retrying webhook in 2 seconds...")
                import time
                time.sleep(2)
        
        print("❌ Failed to send webhook notification after all retries")
        return False

    # ---------------------------
    # Core Processing Functions
    # ---------------------------
    def detect_stamps_in_image(self, image_path: str, template_img: Optional[np.ndarray] = None) -> Dict:
        """Process single image using stamp detection logic"""
        
        # Load and preprocess
        img = self.load_and_preprocess(image_path, width=1600, do_clahe=False)
        img_area = img.shape[0] * img.shape[1]

        # HSV analysis
        hsv = self.to_hsv(img)
        
        # Color mask detection
        color_mask = self.red_mask_from_hsv(hsv, s_thresh=80, v_thresh=60)
        clean_mask = self.morph_clean(color_mask, img.shape, open_frac=0.004, close_frac=0.012)

        # Edge detection
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = self.edges_from_gray(gray, low=60, high=160, blur_ksize=5)

        # Combine masks
        combined = self.combine_mask_and_edges(clean_mask, edges, dilate_iter=1)

        # Find and filter contours
        cnts = self.find_contours(combined)
        candidates = self.filter_contours(cnts, img_area,
                                    min_area_ratio=0.001, max_area_ratio=0.15,
                                    aspect_range=(1.5, 4.0), solidity_min=0.4)

        # Score and collect boxes
        boxes = []
        scores = []
        crops = []
        for idx, (cnt, props) in enumerate(candidates):
            x,y,w,h = props['bbox']
            rect = props['rect']
            crop = self.rotate_crop(img, rect)
            if crop is None or crop.size == 0:
                continue

            # Compute confidence score
            crop_hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
            crop_mask = self.red_mask_from_hsv(crop_hsv, s_thresh=60, v_thresh=40)
            red_ratio = float(np.count_nonzero(crop_mask)) / max(1, crop_mask.size)

            crop_gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            ed = self.edges_from_gray(crop_gray, low=50, high=150, blur_ksize=3)
            edge_density = float(np.count_nonzero(ed)) / max(1, ed.size)

            fine_edges = self.edges_from_gray(crop_gray, low=100, high=200, blur_ksize=1)
            fine_edge_density = float(np.count_nonzero(fine_edges)) / max(1, fine_edges.size)

            orb_score = 0.0
            if template_img is not None:
                orb_score = self.orb_match_score(crop, template_img)

            conf = 0.6 * red_ratio + 0.2 * edge_density - 0.1 * fine_edge_density + 0.3 * orb_score

            if red_ratio < 0.3:
                conf *= 0.5

            boxes.append((x,y,w,h))
            scores.append(conf)
            crops.append(crop)

        # Apply NMS
        if boxes:
            keep_idxs = self.nms(boxes, scores, iou_thresh=0.3)
        else:
            keep_idxs = []

        # Create final results
        image_name = os.path.splitext(os.path.basename(image_path))[0]
        results = []
        for i in keep_idxs:
            x,y,w,h = boxes[i]
            conf = scores[i]
            results.append(dict(
                box=(x,y,w,h), 
                conf=conf
            ))

        return {
            'image_name': image_name,
            'image_path': image_path,
            'stamps_detected': len(results),
            'detection_results': results,
            'original_image': img  # Keep this for VLM processing
        }

    def group_pages_by_student(self, all_results: Dict, image_paths: List[str]) -> Dict:
        """Group pages by student based on stamp detection"""
        
        stamp_pages = []
        for i, image_path in enumerate(image_paths):
            result = all_results.get(image_path, {})
            if result.get('stamps_detected', 0) > 0:
                first_stamp = result['detection_results'][0]
                roll_number = first_stamp.get('roll_number', f"Unknown_Student_{len(stamp_pages)+1}")
                stamp_pages.append({
                    'page_index': i,
                    'page_name': os.path.basename(image_path),
                    'roll_number': roll_number,
                    'total_stamps': result['stamps_detected']
                })

        # Create student groups
        student_groups = []

        for i, stamp_page in enumerate(stamp_pages):
            start_page = stamp_page['page_index']

            if i + 1 < len(stamp_pages):
                end_page = stamp_pages[i + 1]['page_index'] - 1
            else:
                end_page = len(image_paths) - 1

            page_range = list(range(start_page, end_page + 1))
            page_names = [os.path.basename(image_paths[idx]) for idx in page_range]

            student_group = {
                'student_id': i + 1,
                'roll_number': stamp_page['roll_number'],
                'stamp_page': stamp_page['page_name'],
                'start_page_index': start_page,
                'end_page_index': end_page,
                'page_range': f"Page {start_page+1} to {end_page+1}",
                'total_pages': len(page_range),
                'page_indices': page_range,
                'page_names': page_names,
                'stamps_in_first_page': stamp_page['total_stamps']
            }

            student_groups.append(student_group)

        return student_groups

    def process_job(self, job_id: str, webhook_url: Optional[str] = None, crop_percentage: float = 0.2) -> Dict:
        """Main processing function for stamp detection job"""
        
        # Fetch images from S3
        print(f"📥 Fetching images from S3 for job: {job_id}")
        image_paths = self.fetch_images_from_s3(job_id)
        
        if not image_paths:
            raise Exception(f'No images found in S3 for job_id: {job_id}')

        print(f"📋 Found {len(image_paths)} images to process")

        # Optional: Handle template if provided (could be another S3 object or skip for now)
        template_img = None

        # Process each image one by one
        all_results = {}
        pages_with_stamps = []

        for idx, image_path in enumerate(image_paths):
            try:
                print(f"🔍 Processing image {idx+1}/{len(image_paths)}: {os.path.basename(image_path)}")
                
                # Detect stamps
                page_result = self.detect_stamps_in_image(image_path, template_img)
                all_results[image_path] = page_result

                if page_result['stamps_detected'] > 0:
                    pages_with_stamps.append((image_path, page_result))

                    # Process each detected stamp with VLM one by one
                    for stamp_idx, detection in enumerate(page_result['detection_results']):
                        print(f"🔍 Processing stamp {stamp_idx+1}/{len(page_result['detection_results'])} in {page_result['image_name']}")
                        
                        # Crop top percentage of full page image for VLM analysis
                        cropped_page = self.crop_top_percentage(page_result['original_image'], crop_percentage)
                        full_page_roll = self.extract_roll_number_with_vlm(
                            cropped_page, 
                            page_result['image_name']
                        )

                        # Also analyze the stamp crop itself
                        x, y, w, h = detection['box']
                        crop_img = page_result['original_image'][y:y+h, x:x+w]
                        # Apply crop percentage to the stamp region as well
                        cropped_stamp = self.crop_top_percentage(crop_img, crop_percentage)

                        stamp_name = f"{page_result['image_name']}_stamp_{stamp_idx}"
                        stamp_roll = self.extract_roll_number_with_vlm(cropped_stamp, f"{stamp_name}_crop")

                        # Use the result that found a roll number, prefer full page context
                        final_roll_number = full_page_roll or stamp_roll

                        # Store result
                        detection['roll_number'] = final_roll_number
                        detection['roll_from_full_page'] = full_page_roll
                        detection['roll_from_crop'] = stamp_roll
                        detection['vlm_analyzed'] = True
                        
                        print(f"✅ Completed processing stamp {stamp_idx+1} - Roll number: {final_roll_number}")

                print(f"✅ Completed processing image: {page_result['image_name']}")

            except Exception as e:
                print(f"❌ Error processing {image_path}: {str(e)}")
                all_results[image_path] = {'error': str(e)}

        # Group pages by student
        print(f"👥 Grouping pages by student...")
        student_groups = self.group_pages_by_student(all_results, image_paths)

        # Prepare summary statistics
        total_pages = len(all_results)
        total_stamps = sum(r.get('stamps_detected', 0) for r in all_results.values() if 'stamps_detected' in r)
        successful_extractions = []
        
        for image_path, result in all_results.items():
            if 'detection_results' in result:
                for idx, detection in enumerate(result['detection_results']):
                    if detection.get('roll_number'):
                        successful_extractions.append({
                            'page': os.path.basename(image_path),
                            'stamp_idx': idx,
                            'roll_number': detection['roll_number'],
                            'confidence': detection['conf']
                        })

        # Clean up original images from results (remove large image data)
        for result in all_results.values():
            if 'original_image' in result:
                del result['original_image']
            # Convert image_path to just filename for cleaner output
            if 'image_path' in result:
                result['image_filename'] = os.path.basename(result['image_path'])
                del result['image_path']

        # Clean up temporary files
        try:
            temp_job_dir = os.path.join(self.temp_folder, job_id)
            if os.path.exists(temp_job_dir):
                shutil.rmtree(temp_job_dir)
                print(f"🧹 Cleaned up temporary directory: {temp_job_dir}")
        except Exception as e:
            print(f"⚠️ Warning: Could not clean up temp directory: {e}")

        # Prepare final response
        response_data = {
            'job_id': job_id,
            'question_paper_uuid': job_id, # change this to use passed uuid and not create one.
            'processing_summary': {
                'total_pages': total_pages,
                'pages_with_stamps': len(pages_with_stamps),
                'total_stamps_detected': total_stamps,
                'total_roll_numbers_extracted': len(successful_extractions),
                'timestamp': datetime.now().isoformat(),
                'status': 'completed',
                'elapsed_time': 0  # You can track this if needed
            },
            'detailed_results': all_results,
            'student_groups': student_groups,
            'successful_extractions': successful_extractions,
            's3_info': {
                'bucket': self.s3_bucket_name,
                'job_folder': f"{job_id}/",
                'processed_files': [os.path.basename(path) for path in image_paths]
            }
        }

        # Send webhook notification
        webhook_url = webhook_url or self.default_webhook_url
        webhook_sent = self.send_webhook_notification(webhook_url, response_data)
        
        # Add webhook status to response
        response_data['webhook_notification'] = {
            'url': webhook_url,
            'sent_successfully': webhook_sent,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"📤 Webhook notification: {'✅ Sent' if webhook_sent else '❌ Failed'}")
        
        return response_data

    def create_error_response(self, job_id: str, error_message: str, webhook_url: Optional[str] = None) -> Dict:
        """Create error response for failed job processing"""
        error_response = {
            'job_id': job_id,
            'question_paper_uuid': job_id,
            'status': 'error',
            'error': error_message,
            'timestamp': datetime.now().isoformat(),
            'processing_summary': {
                'total_pages': 0,
                'pages_with_stamps': 0,
                'total_stamps_detected': 0,
                'total_roll_numbers_extracted': 0,
                'status': 'failed'
            }
        }
        
        # Clean up on error
        try:
            temp_job_dir = os.path.join(self.temp_folder, job_id)
            if os.path.exists(temp_job_dir):
                shutil.rmtree(temp_job_dir)
        except Exception as cleanup_error:
            print(f"⚠️ Warning: Could not clean up temp directory: {cleanup_error}")
        
        # Send error webhook
        webhook_url = webhook_url or self.default_webhook_url
        webhook_sent = self.send_webhook_notification(webhook_url, error_response)
        
        # Add webhook status to error response
        error_response['webhook_notification'] = {
            'url': webhook_url,
            'sent_successfully': webhook_sent,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"📤 Error webhook notification: {'✅ Sent' if webhook_sent else '❌ Failed'}")
        
        return error_response

    def test_vlm_extraction(self, image_url: str, crop_percentage: float = 0.2) -> Dict:
        """Test VLM extraction with a sample image from URL or S3"""
        try:
            # Download image from URL
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Convert to OpenCV image
            image_array = np.asarray(bytearray(response.content), dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            
            if image is None:
                raise Exception("Failed to decode image")
            
            # Crop top percentage
            cropped_image = self.crop_top_percentage(image, crop_percentage)
            
            # Extract roll number
            image_name = f"test_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            roll_number = self.extract_roll_number_with_vlm(cropped_image, image_name)
            
            return {
                'test_status': 'success',
                'image_url': image_url,
                'crop_percentage': crop_percentage,
                'original_image_shape': image.shape,
                'cropped_image_shape': cropped_image.shape,
                'extracted_roll_number': roll_number,
                'vlm_configured': self.is_openai_configured(),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'test_status': 'failed',
                'error': str(e),
                'image_url': image_url,
                'vlm_configured': self.is_openai_configured(),
                'timestamp': datetime.now().isoformat()
            }