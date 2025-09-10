import os
from flask import Flask
from config import Config
from routes.converter_routes import converter_bp

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH
    
    # Register blueprints
    app.register_blueprint(converter_bp)
    
    return app

def print_startup_info():
    """Print startup information"""
    print("PDF to Images & OCR API Server with S3 Integration")
    print("=" * 60)
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
    print("\nSystem Endpoints:")
    print("  GET /health - Health check")
    print("  GET /s3-config - S3 configuration status")
    print("\nConfiguration:")
    print(f"  S3 Bucket: {Config.S3_BUCKET}")
    print(f"  S3 Region: {Config.AWS_REGION}")
    print(f"  S3 Configured: {'Yes' if Config.AWS_ACCESS_KEY_ID and Config.AWS_SECRET_ACCESS_KEY else 'No'}")
    print(f"  Azure OCR Endpoint: {Config.AZURE_ENDPOINT}")
    print(f"  Django API Base: {Config.DJANGO_API_BASE}")
    print(f"  Webhook URL: {Config.WEBHOOK_URL}")
    print("\nEnvironment Variables:")
    print("  PDF Conversion: S3_BUCKET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION")
    print("  OCR Service: AZURE_SUBSCRIPTION_KEY, AZURE_ENDPOINT, DJANGO_API_BASE, WEBHOOK_URL")
    
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

if __name__ == '__main__':
    # Ensure temp directory exists
    os.makedirs(Config.TEMP_DIR, exist_ok=True)
    
    # Print startup information
    print_startup_info()
    
    # Create and run the app
    app = create_app()
    app.run(debug=True, port=5015)