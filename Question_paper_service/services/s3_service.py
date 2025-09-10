import boto3
import os
import logging
from botocore.exceptions import ClientError, NoCredentialsError
from config import Config

logger = logging.getLogger(__name__)

class S3Service:
    """Service for handling S3 operations"""
    
    def __init__(self):
        self.config = Config.get_s3_config()
        self.bucket = self.config['bucket']
        self.region = self.config['region']
        self.client = None
        
        try:
            if self._has_credentials():
                self.client = boto3.client(
                    's3',
                    aws_access_key_id=self.config['access_key'],
                    aws_secret_access_key=self.config['secret_key'],
                    region_name=self.region
                )
                logger.info(f"S3 client initialized for bucket: {self.bucket}")
            else:
                logger.warning("S3 credentials not provided")
        except Exception as e:
            logger.error(f"S3 client initialization failed: {e}")
    
    def _has_credentials(self):
        """Check if S3 credentials are available"""
        return bool(
            self.config['access_key'] and 
            self.config['secret_key'] and 
            self.bucket
        )
    
    def is_configured(self):
        """Check if S3 service is properly configured"""
        return self.client is not None
    
    def test_connection(self):
        """Test S3 connection by checking bucket access"""
        if not self.is_configured():
            return False
        
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return True
        except Exception as e:
            logger.error(f"S3 connection test failed: {e}")
            return False
    
    def upload_file(self, file_path, s3_key, content_type='application/octet-stream'):
        """Upload a file to S3"""
        if not self.is_configured():
            raise Exception("S3 client not initialized")
        
        try:
            self.client.upload_file(
                file_path,
                self.bucket,
                s3_key,
                ExtraArgs={'ContentType': content_type}
            )
            
            s3_url = f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{s3_key}"
            logger.info(f"Successfully uploaded {file_path} to {s3_key}")
            return s3_url
            
        except ClientError as e:
            logger.error(f"S3 upload failed for {s3_key}: {e}")
            raise Exception(f"S3 upload failed: {e}")
    
    def download_file(self, s3_key):
        """Download a file from S3 and return as bytes"""
        if not self.is_configured():
            raise Exception("S3 client not initialized")
        
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=s3_key)
            return response['Body'].read()
        except ClientError as e:
            logger.error(f"S3 download failed for {s3_key}: {e}")
            raise Exception(f"Failed to download {s3_key} from S3: {e}")
    
    def list_objects(self, prefix=''):
        """List objects in S3 bucket with given prefix"""
        if not self.is_configured():
            raise Exception("S3 client not initialized")
        
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                return []
            
            objects = []
            for obj in response['Contents']:
                objects.append({
                    'key': obj['Key'],
                    'filename': os.path.basename(obj['Key']),
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat() if hasattr(obj['LastModified'], 'isoformat') else str(obj['LastModified'])
                })
            
            return objects
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                raise Exception(f"S3 bucket '{self.bucket}' does not exist")
            elif error_code == 'AccessDenied':
                raise Exception("Access denied to S3 bucket. Check your credentials and permissions")
            else:
                raise Exception(f"S3 error: {e}")
    
    def delete_objects(self, keys):
        """Delete multiple objects from S3"""
        if not self.is_configured():
            raise Exception("S3 client not initialized")
        
        if not keys:
            return []
        
        try:
            objects_to_delete = [{'Key': key} for key in keys]
            
            response = self.client.delete_objects(
                Bucket=self.bucket,
                Delete={'Objects': objects_to_delete}
            )
            
            deleted = response.get('Deleted', [])
            errors = response.get('Errors', [])
            
            if errors:
                logger.warning(f"Some objects failed to delete: {errors}")
            
            logger.info(f"Successfully deleted {len(deleted)} objects from S3")
            return [obj['Key'] for obj in deleted]
            
        except ClientError as e:
            logger.error(f"S3 delete operation failed: {e}")
            raise Exception(f"Failed to delete objects from S3: {e}")
    
    def get_question_paper_images(self, uuid):
        """Get all question paper images from S3 for a given UUID"""
        prefix = f"question-paper/{uuid}/"
        objects = self.list_objects(prefix)
        
        # Filter for image files only (exclude PDF and ZIP files)
        image_files = []
        for obj in objects:
            key = obj['key']
            
            # Skip PDF and ZIP files
            if key.endswith('.pdf') or key.endswith('.zip'):
                continue
            
            # Check if it's an image file
            file_extension = os.path.splitext(key)[1].lower()
            if file_extension in Config.SUPPORTED_EXTENSIONS:
                image_files.append(obj)
        
        # Sort by filename to maintain page order
        image_files.sort(key=lambda x: x['filename'])
        return image_files
    
    def cleanup_job_files(self, job_id):
        """Clean up all S3 files for a specific job"""
        try:
            prefix = f"question-paper/{job_id}/"
            objects = self.list_objects(prefix)
            
            if not objects:
                return []
            
            keys_to_delete = [obj['key'] for obj in objects]
            deleted_keys = self.delete_objects(keys_to_delete)
            
            logger.info(f"Cleaned up {len(deleted_keys)} S3 objects for job {job_id}")
            return deleted_keys
            
        except Exception as e:
            logger.error(f"S3 cleanup failed for job {job_id}: {e}")
            raise
    
    def get_s3_url(self, s3_key):
        """Generate S3 URL for a given key"""
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{s3_key}"
    
    def upload_question_paper_file(self, file_path, job_id, filename, content_type):
        """Upload a file to the question-paper folder structure"""
        s3_key = f"question-paper/{job_id}/{filename}"
        return self.upload_file(file_path, s3_key, content_type)
    
    def get_bucket_info(self):
        """Get S3 bucket information"""
        return {
            'bucket': self.bucket,
            'region': self.region,
            'configured': self.is_configured(),
            'accessible': self.test_connection() if self.is_configured() else False
        }