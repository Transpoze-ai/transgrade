from flask import Flask
import os
import logging
from datetime import datetime

from config import Config

# Import existing blueprints
from routes.pdf_routes import pdf_bp
from routes.ocr_routes import ocr_bp
from routes.scheduler_routes import scheduler_bp

# Import new VLM blueprint
from routes.vlm_routes import vlm_bp

def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL, logging.INFO),
        format=Config.LOG_FORMAT,
        handlers=[
            logging.FileHandler('app.log'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)

    # Create temp directory
    os.makedirs(Config.TEMP_DIR, exist_ok=True)

    # Register existing blueprints
    app.register_blueprint(pdf_bp, url_prefix='/apils/pdf')
    app.register_blueprint(ocr_bp, url_prefix='/apils/ocr')
    app.register_blueprint(scheduler_bp, url_prefix='/apils/scheduler')
    
    # Register new VLM blueprint
    app.register_blueprint(vlm_bp, url_prefix='/apils/vlm')

    @app.route('/apils/health', methods=['GET'])
    def health():
        """Combined health check for all services"""
        from services.s3_service import S3Service
        from services.scheduler_service import SchedulerService
        from services.vlm_service import VLMService
        import requests

        try:
            # Check S3 service
            s3_service = S3Service()
            s3_status = s3_service.test_connection()

            # Check Django API
            django_status = False
            try:
                django_health = requests.get(f'{Config.DJANGO_API_BASE_URL}/status/', timeout=Config.HEALTH_CHECK_TIMEOUT)
                django_status = django_health.status_code == 200
            except:
                pass
            
            # Check scheduler service health
            scheduler_service = SchedulerService()
            scheduler_health = scheduler_service.check_health()
            
            # Check VLM service health
            vlm_service = VLMService()
            vlm_health = vlm_service.check_health()
            
            return {
                'success': True,
                'message': 'Combined Question Paper Processing Service is running',
                'timestamp': datetime.now().isoformat(),
                'services': {
                    'pdf_processing': {
                        'status': 'active',
                        's3_configured': s3_service.is_configured(),
                        's3_connected': s3_status
                    },
                    'ocr_processing': {
                        'status': 'active',
                        'azure_configured': bool(Config.AZURE_SUBSCRIPTION_KEY and Config.AZURE_ENDPOINT),
                        'django_connected': django_status
                    },
                    'scheduler_service': {
                        'status': 'active' if scheduler_health['success'] else 'error',
                        'external_services': scheduler_health.get('external_services', {}),
                        'last_check': scheduler_health.get('timestamp')
                    },
                    'vlm_service': {
                        'status': 'active' if vlm_health['success'] else 'error',
                        'openai_configured': vlm_health['details'].get('openai_configured', False),
                        'openai_connected': vlm_health['details'].get('openai_connected', False),
                        'model': vlm_health['details'].get('openai_model', 'N/A'),
                        'last_check': datetime.now().isoformat()
                    }
                },
                'configuration': {
                    's3_bucket': Config.S3_BUCKET,
                    'aws_region': Config.AWS_REGION,
                    'django_api_url': Config.DJANGO_API_BASE_URL,
                    'max_file_size_mb': Config.MAX_CONTENT_LENGTH // (1024*1024),
                    'temp_directory': Config.TEMP_DIR,
                    'openai_model': Config.OPENAI_VLM_MODEL
                }
            }
        except Exception as e:
            logger.error(f'Health check failed: {str(e)}')
            return {
                'success': False,
                'error': f'Health check failed: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }, 500
    
    @app.route('/apils/config', methods=['GET'])
    def get_configuration():
        """Get service configuration information"""
        try:
            validation = Config.validate_config()
            
            return {
                'service_name': 'Question Paper Processing Service',
                'version': '2.1.0',
                'configuration_valid': validation['valid'],
                'missing_variables': validation.get('missing_vars', []),
                'warnings': validation.get('warnings', []),
                'services': {
                    'pdf_processing': {
                        'max_file_size_mb': Config.MAX_CONTENT_LENGTH // (1024*1024),
                        'default_dpi': Config.DEFAULT_DPI,
                        'supported_formats': Config.SUPPORTED_EXTENSIONS,
                        'batch_size': Config.BATCH_SIZE
                    },
                    'ocr_processing': {
                        'azure_configured': bool(Config.AZURE_SUBSCRIPTION_KEY and Config.AZURE_ENDPOINT),
                        'max_dimension': Config.MAX_DIMENSION,
                        'min_dimension': Config.MIN_DIMENSION,
                        'supported_extensions': Config.SUPPORTED_EXTENSIONS
                    },
                    'scheduler_service': {
                        'rubric_generation_url': Config.RUBRIC_GENERATION_API_URL,
                        'process_rubric_url': Config.PROCESS_RUBRIC_API_URL,
                        'timeout_seconds': Config.DJANGO_API_TIMEOUT
                    },
                    'vlm_service': {
                        'openai_configured': bool(Config.OPENAI_API_KEY),
                        'model': Config.OPENAI_VLM_MODEL,
                        'max_tokens': Config.OPENAI_MAX_TOKENS,
                        'temperature': Config.OPENAI_TEMPERATURE,
                        'supported_formats': Config.SUPPORTED_EXTENSIONS
                    }
                },
                'external_apis': {
                    'django_api': Config.DJANGO_API_BASE_URL,
                    'rubric_generation': Config.RUBRIC_GENERATION_API_URL,
                    'process_rubric': Config.PROCESS_RUBRIC_API_URL,
                    'openai_api': 'https://api.openai.com/v1'
                }
            }
        except Exception as e:
            logger.error(f'Configuration check failed: {str(e)}')
            return {
                'success': False,
                'error': f'Configuration check failed: {str(e)}'
            }, 500
    
    @app.route('/apils/s3-config', methods=['GET'])
    def s3_config():
        """Get S3 configuration status"""
        from services.s3_service import S3Service
        
        s3_service = S3Service()
        
        return {
            'configured': s3_service.is_configured(),
            'bucket': Config.S3_BUCKET if s3_service.is_configured() else None,
            'region': Config.AWS_REGION,
            'has_credentials': bool(Config.AWS_ACCESS_KEY_ID and Config.AWS_SECRET_ACCESS_KEY),
            'question_paper_prefix': 'question-paper/',
            'supported_by_services': {
                'pdf_processing': True,
                'ocr_processing': True,
                'vlm_processing': True
            }
        }
    
    @app.route('/', methods=['GET'])
    def root():
        """Root endpoint with service information"""
        return {
            'service': 'Question Paper Processing Service',
            'version': '2.1.0',
            'description': 'Combined PDF Conversion, OCR Processing, VLM Analysis, and Rubric Generation Service',
            'endpoints': {
                'health': 'GET /api/health',
                'configuration': 'GET /api/config',
                's3_config': 'GET /api/s3-config',
                'pdf_processing': {
                    'convert': 'POST /api/pdf/convert',
                    'status': 'GET /api/pdf/status/<job_id>'
                },
                'ocr_processing': {
                    'process': 'POST /api/ocr/process'
                },
                'vlm_processing': {
                    'process_and_save': 'GET /api/vlm/process-images/<uuid>',
                    'process_only': 'GET /api/vlm/process-images-only/<uuid>',
                    'health': 'GET /api/vlm/health',
                    'status': 'GET /api/vlm/status',
                    'debug_s3': 'GET /api/vlm/debug/s3/<uuid>'
                },
                'scheduler_service': {
                    'generate_rubric': 'POST /api/scheduler/generate-rubric-from-uuid',
                    'health': 'GET /api/scheduler/health',
                    'status': 'GET /api/scheduler/status'
                }
            },
            'documentation': 'See individual endpoint documentation for detailed usage'
        }
    
    @app.errorhandler(404)
    def not_found(error):
        return {
            'success': False,
            'error': 'Endpoint not found',
            'available_services': {
                'pdf_processing': [
                    'POST /api/pdf/convert',
                    'GET /api/pdf/status/<job_id>'
                ],
                'ocr_processing': [
                    'POST /api/ocr/process'
                ],
                'vlm_processing': [
                    'GET /api/vlm/process-images/<uuid>',
                    'GET /api/vlm/process-images-only/<uuid>',
                    'GET /api/vlm/health',
                    'GET /api/vlm/status',
                    'GET /api/vlm/debug/s3/<uuid>'
                ],
                'scheduler_service': [
                    'POST /api/scheduler/generate-rubric-from-uuid',
                    'GET /api/scheduler/health',
                    'GET /api/scheduler/status'
                ],
                'general': [
                    'GET /api/health',
                    'GET /api/config',
                    'GET /api/s3-config'
                ]
            }
        }, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f'Internal server error: {str(error)}')
        return {
            'success': False,
            'error': 'Internal server error occurred'
        }, 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    
    print("Question Paper Processing Service")
    print("=" * 60)
    print("Combined PDF + OCR + VLM + Rubric Generation Service")
    print(f"\nVersion: 2.1.0")
    print(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    
    # Print configuration validation
    validation = Config.validate_config()
    Config.print_config_summary()
    
    print("\n" + "=" * 60)
    print("Available Services:")
    print("  📄 PDF Processing - Convert PDFs to images")
    print("  👁  OCR Processing - Extract text from images") 
    print("  🤖 VLM Processing - Extract diagrams and equations using GPT-4 Vision")
    print("  📋 Scheduler Service - Generate rubrics from question papers")
    
    print("\nMain Endpoints:")
    print("  GET  / - Service information")
    print("  GET  /api/health - Combined health check")
    print("  GET  /api/config - Configuration status")
    print("  POST /api/pdf/convert - Convert PDF to images")
    print("  POST /api/ocr/process - Process images with OCR")
    print("  GET  /api/vlm/process-images/<uuid> - Process images with VLM and save")
    print("  GET  /api/vlm/process-images-only/<uuid> - Process images with VLM (test)")
    print("  POST /api/scheduler/generate-rubric-from-uuid - Generate rubrics")
    
    print("\nVLM Service Endpoints:")
    print("  GET  /api/vlm/health - VLM service health")
    print("  GET  /api/vlm/status - VLM service status and info")
    print("  GET  /api/vlm/debug/s3/<uuid> - Debug S3 structure")
    
    print("\nExternal Dependencies:")
    print(f"  S3 Bucket: {Config.S3_BUCKET}")
    print(f"  Azure OCR: {'✓' if Config.AZURE_SUBSCRIPTION_KEY else '✗'}")
    print(f"  OpenAI API: {'✓' if Config.OPENAI_API_KEY else '✗'}")
    print(f"  Django API: {Config.DJANGO_API_BASE_URL}")
    print(f"  Rubric API: {Config.RUBRIC_GENERATION_API_URL}")
    
    print("\nService Features:")
    print("  • PDF to Image Conversion")
    print("  • Azure OCR Text Extraction")
    print("  • GPT-4 Vision Diagram Detection")
    print("  • Automated Rubric Generation")
    print("  • S3 Storage Integration")
    print("  • Django Database Integration")
    
    if not validation['valid']:
        print(f"\n⚠️  CONFIGURATION ISSUES:")
        for var in validation['missing_vars']:
            print(f"     Missing: {var}")
    
    if validation.get('warnings'):
        print(f"\n⚠️  WARNINGS:")
        for warning in validation['warnings']:
            print(f"     {warning}")
    
    print("\n" + "=" * 60)
    
    app.run(host='0.0.0.0', port=5111, debug=True)