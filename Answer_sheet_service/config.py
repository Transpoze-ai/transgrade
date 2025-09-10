import os

class Config:
    # Flask Configuration
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 100 * 1024 * 1024))  # 100MB max file size
    
    # S3 Configuration
    S3_BUCKET = os.environ.get('S3_BUCKET')
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.environ.get('AWS_REGION')
    
    # Conversion Settings
    DEFAULT_DPI = int(os.environ.get('DEFAULT_DPI', 200))
    DEFAULT_FORMAT = os.environ.get('DEFAULT_FORMAT', 'JPEG')
    DEFAULT_QUALITY = int(os.environ.get('DEFAULT_QUALITY', 85))
    BATCH_SIZE = int(os.environ.get('BATCH_SIZE', 5))
    THREAD_COUNT = int(os.environ.get('THREAD_COUNT', 2))
    
    # Directory Settings
    TEMP_DIR = os.environ.get('TEMP_DIR', 'temp')
    
    # Azure OCR Configuration
    AZURE_SUBSCRIPTION_KEY = os.environ.get('AZURE_SUBSCRIPTION_KEY')
    AZURE_ENDPOINT = os.environ.get('AZURE_ENDPOINT')
    
    # Django API Configuration
    DJANGO_API_BASE = os.environ.get('DJANGO_API_BASE')
    WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
    WEBHOOK_TIMEOUT = int(os.environ.get('WEBHOOK_TIMEOUT', 30))
    WEBHOOK_MAX_RETRIES = int(os.environ.get('WEBHOOK_MAX_RETRIES', 3))
    
    # Azure OCR Limits
    MIN_DIMENSION = int(os.environ.get('MIN_DIMENSION', 50))
    MAX_DIMENSION = int(os.environ.get('MAX_DIMENSION', 10000))
    MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', 4 * 1024 * 1024))  # 4MB in bytes