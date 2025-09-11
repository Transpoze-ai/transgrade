import os
from flask import Flask
from config import Config
from routes.converter_routes import converter_bp
from routes.stamp_routes import stamp_bp
from routes.ocr_routes import ocr_bp
from routes.chunker_routes import chunker_bp  # Add this import

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH
    
    # Register blueprints
    app.register_blueprint(converter_bp)
    app.register_blueprint(stamp_bp, url_prefix='/stamp')
    app.register_blueprint(ocr_bp)
    app.register_blueprint(chunker_bp)  # Add this line to register chunker blueprint
    
    return app

def print_startup_info():
    """Print startup information"""
    print("PDF to Images & OCR API Server with S3 Integration, Stamp Detection & Semantic Chunker")
    print("=" * 85)
    print("PDF Conversion Endpoints:")
    print("  POST /convert - Convert PDF to images")
    print("  GET /status/<job_id> - Check conversion status")
    print("  GET /download/<job_id> - Download images ZIP (local)")
    print("  GET /s3-info/<job_id> - Get S3 URLs and info")
    print("  DELETE /cleanup/<job_id> - Clean up local job files")
    print("  DELETE /cleanup-s3/<job_id> - Clean up S3 job files")
    print("  GET /jobs - List all jobs")
    
    print("\nOCR Endpoints:")
    print("  POST /ocr/roll/<roll_no>/uuid/<uuid> - Perform OCR on answer sheets")
    print("  GET /ocr/test-django - Test Django API connection")
    
    print("\nSemantic Chunker Endpoints:")
    print("  GET /chunker - Chunker service health check")
    print("  POST /chunker/process-ocr-chunks - Process OCR data into semantic chunks")
    print("  GET /chunker/test-django-connection - Test Django API connection")
    print("  GET /chunker/test-openai?api_key=... - Test OpenAI API connection")
    print("  GET /chunker/debug/webhook-config - Check webhook configuration")
    print("  POST /chunker/debug/test-webhook - Test webhook notification")
    
    print("\nStamp Detection Endpoints:")
    print("  POST /stamp/process-stamps/<job_id> - Process images from S3 for stamp detection")
    print("  GET /stamp/health - Stamp detection service health check")
    print("  GET /stamp/config - Stamp detection service configuration")
    print("  POST /stamp/test-vlm - Test VLM extraction with sample image")
    
    print("\nSystem Endpoints:")
    print("  GET /health - Health check")
    print("  GET /s3-config - S3 configuration status")
    
    print("\nConfiguration:")
    print(f"  S3 Bucket: {Config.S3_BUCKET}")
    print(f"  S3 Region: {Config.AWS_REGION}")
    print(f"  S3 Configured: {'Yes' if Config.AWS_ACCESS_KEY_ID and Config.AWS_SECRET_ACCESS_KEY else 'No'}")
    print(f"  Azure OCR Endpoint: {Config.AZURE_ENDPOINT}")
    print(f"  Django API Base: {Config.DJANGO_API_BASE}")
    print(f"  OCR Webhook URL: {Config.WEBHOOK_URL}")
    print(f"  Stamp Webhook URL: {Config.STAMP_WEBHOOK_URL}")
    print(f"  Chunker Webhook URL: {Config.CHUNKER_WEBHOOK_URL}")
    print(f"  OpenAI API Configured: {'Yes' if Config.OPENAI_API_KEY and Config.OPENAI_API_KEY != 'sk-proj-YOUR_ACTUAL_API_KEY_HERE' else 'No'}")
    print(f"  Chunker Max Chunk Size: {Config.CHUNKER_DEFAULT_MAX_CHUNK_SIZE}")
    print(f"  Chunker OpenAI Model: {Config.CHUNKER_OPENAI_MODEL}")
    
    print("\nEnvironment Variables:")
    print("  PDF Conversion: S3_BUCKET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION")
    print("  OCR Service: AZURE_SUBSCRIPTION_KEY, AZURE_ENDPOINT, DJANGO_API_BASE, WEBHOOK_URL")
    print("  Stamp Detection: OPENAI_API_KEY, STAMP_WEBHOOK_URL, DEFAULT_CROP_PERCENTAGE")
    print("  Chunker Service: CHUNKER_WEBHOOK_URL, CHUNKER_DEFAULT_MAX_CHUNK_SIZE, CHUNKER_OPENAI_MODEL")
    
    # Check for required dependencies
    try:
        from PIL import Image
        print("\n✓ PIL (Pillow) available for image processing")
    except ImportError:
        print("\n✗ ERROR: PIL (Pillow) not available. Install with: pip install Pillow")
    
    try:
        import requests
        print("✓ Requests library available")
    except ImportError:
        print("✗ ERROR: Requests library not available. Install with: pip install requests")
    
    try:
        import cv2
        print("✓ OpenCV available for stamp detection")
    except ImportError:
        print("✗ ERROR: OpenCV not available. Install with: pip install opencv-python")
    
    try:
        import numpy as np
        print("✓ NumPy available")
    except ImportError:
        print("✗ ERROR: NumPy not available. Install with: pip install numpy")
    
    try:
        import boto3
        print("✓ Boto3 available for S3 operations")
    except ImportError:
        print("✗ ERROR: Boto3 not available. Install with: pip install boto3")
    
    try:
        import openai
        print("✓ OpenAI library available for semantic chunking")
    except ImportError:
        print("✗ ERROR: OpenAI library not available. Install with: pip install openai")

if __name__ == '__main__':
    # Ensure temp directory exists
    os.makedirs(Config.TEMP_DIR, exist_ok=True)
    
    # Print startup information
    print_startup_info()
    
    # Create and run the app
    app = create_app()
    app.run(debug=True, port=5015)