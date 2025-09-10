import os

class Config:
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    OPENAI_VLM_MODEL = os.environ.get('OPENAI_VLM_MODEL', 'gpt-4o')
    OPENAI_MAX_TOKENS = int(os.environ.get('OPENAI_MAX_TOKENS', 300))
    OPENAI_TEMPERATURE = float(os.environ.get('OPENAI_TEMPERATURE', 0.1))

    SECRET_KEY = os.environ.get('SECRET_KEY')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 100 * 1024 * 1024))

    S3_BUCKET = os.environ.get('S3_BUCKET')
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.environ.get('AWS_REGION', 'ap-south-1')

    AZURE_SUBSCRIPTION_KEY = os.environ.get('AZURE_SUBSCRIPTION_KEY')
    AZURE_ENDPOINT = os.environ.get('AZURE_ENDPOINT')
    AZURE_READ_URL = f"{AZURE_ENDPOINT}vision/v3.2/read/analyze" if AZURE_ENDPOINT else None

    DJANGO_API_BASE_URL = os.environ.get('DJANGO_API_BASE_URL')
    DJANGO_PROCESS_ENDPOINT = f"{DJANGO_API_BASE_URL}/process-qp-json/"

    RUBRIC_GENERATION_API_URL = os.environ.get('RUBRIC_GENERATION_API_URL')
    PROCESS_RUBRIC_API_URL = os.environ.get('PROCESS_RUBRIC_API_URL')

    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
