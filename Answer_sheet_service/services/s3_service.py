import boto3
from botocore.exceptions import ClientError
from config import Config

class S3Service:
    def __init__(self):
        self.client = None
        self.bucket = Config.S3_BUCKET
        self.region = Config.AWS_REGION
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize S3 client"""
        try:
            self.client = boto3.client(
                's3',
                aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
                region_name=Config.AWS_REGION
            )
            print(f"S3 client initialized for bucket: {Config.S3_BUCKET}")
        except Exception as e:
            print(f"Warning: S3 client initialization failed: {e}")
            self.client = None
    
    def is_configured(self):
        """Check if S3 is properly configured"""
        return self.client is not None
    
    def upload_file(self, file_path, s3_key, content_type='image/jpeg'):
        """
        Upload a file to S3
        
        Args:
            file_path (str): Local file path
            s3_key (str): S3 object key
            content_type (str): MIME type of the file
            
        Returns:
            str: S3 URL of uploaded file
            
        Raises:
            Exception: If upload fails or client not initialized
        """
        if not self.client:
            raise Exception("S3 client not initialized")
        
        try:
            self.client.upload_file(
                file_path, 
                self.bucket, 
                s3_key,
                ExtraArgs={'ContentType': content_type}
            )
            return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{s3_key}"
        except ClientError as e:
            raise Exception(f"S3 upload failed: {e}")
    
    def delete_objects(self, job_id):
        """
        Delete all objects in a job folder
        
        Args:
            job_id (str): Job ID (used as folder prefix)
            
        Returns:
            dict: Result containing deleted objects info
            
        Raises:
            Exception: If deletion fails or client not initialized
        """
        if not self.client:
            raise Exception("S3 client not initialized")
        
        try:
            # List objects in the job folder
            response = self.client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=f"{job_id}/"
            )
            
            if 'Contents' in response:
                objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
                
                if objects_to_delete:
                    self.client.delete_objects(
                        Bucket=self.bucket,
                        Delete={'Objects': objects_to_delete}
                    )
                    
                    return {
                        'success': True,
                        'deleted_count': len(objects_to_delete),
                        'deleted_objects': [obj['Key'] for obj in objects_to_delete]
                    }
                else:
                    return {
                        'success': True,
                        'deleted_count': 0,
                        'message': 'No objects found to delete'
                    }
            else:
                return {
                    'success': True,
                    'deleted_count': 0,
                    'message': 'No objects found to delete'
                }
                
        except Exception as e:
            raise Exception(f"S3 cleanup failed: {str(e)}")
    
    def download_file(self, s3_url):
        """Download a file from S3 given its URL"""
        if not self.client:
            return None, "S3 client not initialized"
        
        try:
            # Parse S3 URL to extract bucket and key
            if '.s3.amazonaws.com/' in s3_url:
                parts = s3_url.split('.s3.amazonaws.com/')
                bucket_name = parts[0].split('https://')[-1]
                key = parts[1]
            elif '.s3.' in s3_url and '.amazonaws.com/' in s3_url:
                # Regional S3 URL format
                parts = s3_url.split('.amazonaws.com/')
                bucket_name = parts[0].split('https://')[-1].split('.s3.')[0]
                key = parts[1]
            else:
                return None, f"Unrecognized S3 URL format: {s3_url}"
            
            print(f"Downloading from S3 - Bucket: {bucket_name}, Key: {key}")
            
            # Download the object
            response = self.client.get_object(Bucket=bucket_name, Key=key)
            return response['Body'].read(), None
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                return None, f"File not found in S3: {key}"
            elif error_code == 'AccessDenied':
                return None, f"Access denied to S3 object: {bucket_name}/{key}"
            else:
                return None, f"S3 error: {e}"
        except Exception as e:
            return None, f"Error downloading from S3: {str(e)}"
    
    def get_config_info(self):
        """Get S3 configuration information"""
        return {
            'configured': self.is_configured(),
            'bucket': self.bucket,
            'region': self.region,
            'has_credentials': bool(Config.AWS_ACCESS_KEY_ID and Config.AWS_SECRET_ACCESS_KEY)
        }