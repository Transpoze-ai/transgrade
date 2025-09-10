import os
import time
import uuid
import logging
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

def validate_uuid(uuid_string):
    """Validate UUID format and return UUID object or None"""
    try:
        return uuid.UUID(uuid_string)
    except (ValueError, TypeError):
        return None

def generate_job_id():
    """Generate a new UUID for job tracking"""
    return str(uuid.uuid4())

def secure_file_path(filename, base_dir='temp'):
    """Generate secure file path for uploaded files"""
    if not filename:
        raise ValueError("Filename cannot be empty")
    
    # Secure the filename
    safe_filename = secure_filename(filename)
    if not safe_filename:
        # If secure_filename returns empty, generate a safe name
        timestamp = str(int(time.time()))
        safe_filename = f"upload_{timestamp}.pdf"
    
    # Ensure directory exists
    os.makedirs(base_dir, exist_ok=True)
    
    return os.path.join(base_dir, safe_filename)

def format_file_size(size_bytes):
    """Format file size in bytes to human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def format_duration(seconds):
    """Format duration in seconds to human readable format"""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"

def cleanup_old_files(directory, max_age_hours=24):
    """Clean up files older than specified hours"""
    if not os.path.exists(directory):
        return []
    
    cutoff_time = time.time() - (max_age_hours * 3600)
    deleted_files = []
    
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            
            # Skip directories
            if os.path.isdir(file_path):
                continue
            
            # Check file age
            file_mtime = os.path.getmtime(file_path)
            if file_mtime < cutoff_time:
                try:
                    os.remove(file_path)
                    deleted_files.append(filename)
                    logger.info(f"Deleted old file: {filename}")
                except OSError as e:
                    logger.warning(f"Failed to delete {filename}: {e}")
    
    except OSError as e:
        logger.error(f"Error accessing directory {directory}: {e}")
    
    return deleted_files

def validate_request_json(request, required_fields):
    """Validate JSON request and required fields"""
    try:
        data = request.get_json()
        if not data:
            return None, "Request body must be valid JSON"
        
        missing_fields = []
        for field in required_fields:
            if field not in data or data[field] is None:
                missing_fields.append(field)
        
        if missing_fields:
            return None, f"Missing required fields: {', '.join(missing_fields)}"
        
        return data, None
        
    except Exception as e:
        return None, f"Invalid JSON: {str(e)}"

def validate_file_upload(request, file_field='pdf_file', allowed_extensions=None):
    """Validate file upload in request"""
    if allowed_extensions is None:
        allowed_extensions = ['.pdf']
    
    if file_field not in request.files:
        return None, f"No {file_field} provided"
    
    file = request.files[file_field]
    if file.filename == '':
        return None, "No file selected"
    
    # Check file extension
    if file.filename:
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return None, f"File must be one of: {', '.join(allowed_extensions)}"
    
    return file, None

def create_response(success=True, message=None, data=None, error=None, **kwargs):
    """Create standardized API response"""
    response = {
        'success': success,
        'timestamp': datetime.now().isoformat()
    }
    
    if message:
        response['message'] = message
    
    if error:
        response['error'] = error
    
    if data:
        response.update(data)
    
    # Add any additional kwargs
    response.update(kwargs)
    
    return response

def log_request_info(request, additional_info=None):
    """Log incoming request information"""
    try:
        info = {
            'method': request.method,
            'path': request.path,
            'remote_addr': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', 'Unknown'),
            'content_length': request.content_length
        }
        
        if additional_info:
            info.update(additional_info)
        
        logger.info(f"Request: {info}")
        
    except Exception as e:
        logger.warning(f"Failed to log request info: {e}")

def rate_limit(max_requests=10, window_minutes=1):
    """Simple in-memory rate limiting decorator"""
    requests_log = {}
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request, jsonify
            
            # Use IP address as identifier
            client_id = request.remote_addr
            current_time = datetime.now()
            window_start = current_time - timedelta(minutes=window_minutes)
            
            # Clean old entries
            if client_id in requests_log:
                requests_log[client_id] = [
                    req_time for req_time in requests_log[client_id] 
                    if req_time > window_start
                ]
            else:
                requests_log[client_id] = []
            
            # Check rate limit
            if len(requests_log[client_id]) >= max_requests:
                logger.warning(f"Rate limit exceeded for {client_id}")
                return jsonify(create_response(
                    success=False,
                    error=f"Rate limit exceeded. Max {max_requests} requests per {window_minutes} minutes."
                )), 429
            
            # Add current request
            requests_log[client_id].append(current_time)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def safe_int(value, default=None, min_val=None, max_val=None):
    """Safely convert value to integer with validation"""
    try:
        result = int(value)
        
        if min_val is not None and result < min_val:
            return default
        if max_val is not None and result > max_val:
            return default
        
        return result
    except (ValueError, TypeError):
        return default

def safe_float(value, default=None, min_val=None, max_val=None):
    """Safely convert value to float with validation"""
    try:
        result = float(value)
        
        if min_val is not None and result < min_val:
            return default
        if max_val is not None and result > max_val:
            return default
        
        return result
    except (ValueError, TypeError):
        return default

def get_content_type(filename):
    """Get content type based on file extension"""
    ext = os.path.splitext(filename)[1].lower()
    
    content_types = {
        '.pdf': 'application/pdf',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.tiff': 'image/tiff',
        '.tif': 'image/tiff',
        '.webp': 'image/webp',
        '.zip': 'application/zip',
        '.json': 'application/json'
    }
    
    return content_types.get(ext, 'application/octet-stream')

def sanitize_filename(filename):
    """Sanitize filename for safe storage"""
    if not filename:
        return f"file_{int(time.time())}"
    
    # Remove path components
    filename = os.path.basename(filename)
    
    # Use werkzeug's secure_filename
    safe_name = secure_filename(filename)
    
    # If nothing left, generate a name
    if not safe_name:
        timestamp = str(int(time.time()))
        return f"file_{timestamp}"
    
    return safe_name

def is_valid_image_file(filename):
    """Check if filename has a valid image extension"""
    from config import Config
    
    if not filename:
        return False
    
    ext = os.path.splitext(filename)[1].lower()
    return ext in Config.SUPPORTED_EXTENSIONS

def truncate_text(text, max_length=100, suffix='...'):
    """Truncate text to specified length"""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

class JobTracker:
    """Simple job status tracking utility"""
    
    def __init__(self):
        self.jobs = {}
    
    def create_job(self, job_id, job_type='unknown', **initial_data):
        """Create a new job entry"""
        self.jobs[job_id] = {
            'id': job_id,
            'type': job_type,
            'status': 'created',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            **initial_data
        }
        return job_id
    
    def update_job(self, job_id, **updates):
        """Update job data"""
        if job_id not in self.jobs:
            return False
        
        self.jobs[job_id].update(updates)
        self.jobs[job_id]['updated_at'] = datetime.now().isoformat()
        return True
    
    def get_job(self, job_id):
        """Get job data"""
        return self.jobs.get(job_id)
    
    def delete_job(self, job_id):
        """Delete job entry"""
        return self.jobs.pop(job_id, None)
    
    def list_jobs(self, job_type=None, status=None):
        """List jobs with optional filtering"""
        jobs = list(self.jobs.values())
        
        if job_type:
            jobs = [job for job in jobs if job.get('type') == job_type]
        
        if status:
            jobs = [job for job in jobs if job.get('status') == status]
        
        return jobs
    
    def cleanup_old_jobs(self, max_age_hours=24):
        """Remove jobs older than specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        old_jobs = []
        for job_id, job in list(self.jobs.items()):
            try:
                created_at = datetime.fromisoformat(job['created_at'])
                if created_at < cutoff_time:
                    old_jobs.append(job_id)
                    del self.jobs[job_id]
            except (KeyError, ValueError):
                # Invalid timestamp, remove job
                old_jobs.append(job_id)
                del self.jobs[job_id]
        
        return old_jobs