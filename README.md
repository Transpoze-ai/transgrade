Question Paper Processing Services

A comprehensive microservices architecture for processing question papers, answer sheets, and educational content with AI-powered analysis and automated workflows.
🏗️ Architecture Overview
This repository contains two main Flask-based services that work together to provide a complete question paper processing pipeline:
Service 1: Question Paper Processing Service (Port 5111)
Main Service - Handles PDF conversion, OCR, VLM analysis, and rubric generation
Service 2: Answer Sheet Processing Service (Port 5015)
Processing Service - Handles PDF conversion, OCR, stamp detection, and semantic chunking
🚀 Services Overview
Question Paper Processing Service
Port: 5111 | Version: 2.1.0
A unified service combining multiple AI-powered processing capabilities:

📄 PDF Processing - Convert PDFs to high-quality images
👁️ OCR Processing - Extract text using Azure Cognitive Services
🤖 VLM Processing - Analyze diagrams and equations using GPT-4 Vision
📋 Scheduler Service - Generate automated rubrics from question papers

Key Endpoints:
GET  /apils/health                              - Combined health check
GET  /apils/config                              - Configuration status
POST /apils/pdf/convert                         - Convert PDF to images
POST /apils/ocr/process                         - Process images with OCR
GET  /apils/vlm/process-images/<uuid>           - Process with VLM and save
POST /apils/scheduler/generate-rubric-from-uuid - Generate rubrics
Answer Sheet Processing Service
Port: 5015
Specialized service for answer sheet processing and content analysis:

📄 PDF Conversion - Convert answer sheets to images with S3 integration
👁️ OCR Processing - Extract student responses from answer sheets
🔍 Stamp Detection - Detect and analyze evaluation stamps using computer vision
🧠 Semantic Chunking - Process OCR content into meaningful semantic chunks using OpenAI

Key Endpoints:
POST /convert                                   - Convert PDF to images
GET  /status/<job_id>                          - Check conversion status
POST /ocr/roll/<roll_no>/uuid/<uuid>           - Perform OCR on answer sheets
POST /stamp/process-stamps/<job_id>            - Process stamp detection
POST /chunker/process-ocr-chunks               - Generate semantic chunks
🛠️ Technology Stack
Core Technologies

Flask - Web framework for both services
Python 3.x - Primary programming language
Docker - Containerization support

AI & ML Services

Azure Cognitive Services - OCR text extraction
OpenAI GPT-4 Vision - Diagram and equation analysis
OpenCV - Computer vision for stamp detection
OpenAI GPT Models - Semantic text chunking

Storage & Infrastructure

AWS S3 - File storage and management
Django API - Backend database integration
RESTful APIs - Service communication

Image Processing

Pillow (PIL) - Image manipulation
pdf2image - PDF to image conversion
NumPy - Numerical computations

📋 Prerequisites
System Requirements

Python 3.8+
Docker (optional)
Sufficient storage for temporary file processing

Required Environment Variables
AWS Configuration
envAWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=your_region
S3_BUCKET=your_bucket_name
Azure Cognitive Services
envAZURE_SUBSCRIPTION_KEY=your_azure_key
AZURE_ENDPOINT=your_azure_endpoint
OpenAI Configuration
envOPENAI_API_KEY=your_openai_key
OPENAI_VLM_MODEL=gpt-4-vision-preview
Django API Integration
envDJANGO_API_BASE_URL=your_django_api_url
RUBRIC_GENERATION_API_URL=your_rubric_api_url
PROCESS_RUBRIC_API_URL=your_process_rubric_url
Webhook URLs
envWEBHOOK_URL=your_ocr_webhook_url
STAMP_WEBHOOK_URL=your_stamp_webhook_url
CHUNKER_WEBHOOK_URL=your_chunker_webhook_url
🚀 Quick Start
Option 1: Direct Python Execution

Clone the repository

bash   git clone <repository-url>
   cd question-paper-services

Install dependencies

bash   pip install -r requirements.txt

Set environment variables

bash   cp .env.example .env
   # Edit .env with your configuration

Start the services

bash   # Terminal 1 - Question Paper Processing Service
   python main.py  # Runs on port 5111
   
   # Terminal 2 - Answer Sheet Processing Service
   python answer_sheet_main.py  # Runs on port 5015
Option 2: Docker Deployment
bash# Build and run Question Paper Processing Service
docker build -t qp-processing-service .
docker run -p 5111:5111 --env-file .env qp-processing-service

# Build and run Answer Sheet Processing Service
docker build -t answer-sheet-service -f Dockerfile.answer .
docker run -p 5015:5015 --env-file .env answer-sheet-service
🔍 Service Health Checks
Question Paper Processing Service
bashcurl http://localhost:5111/apils/health
Answer Sheet Processing Service
bashcurl http://localhost:5015/health
📊 Monitoring and Logging
Both services provide comprehensive logging and monitoring:

Health Endpoints - Real-time service status
Configuration Endpoints - Current settings and validation
File Logging - Persistent log files
Console Logging - Real-time debug information

🔧 Configuration Management
Services use a centralized configuration system with validation:

Environment variable validation
Missing configuration detection
Service dependency checks
External API connectivity verification

📈 Scalability Features

Asynchronous Processing - Non-blocking operations
S3 Integration - Scalable file storage
Microservices Architecture - Independent scaling
RESTful APIs - Easy integration and expansion

🛡️ Security Considerations

API key management through environment variables
Secure file handling with temporary directories
Input validation and sanitization
Error handling without information leakage

🤝 API Integration
External Service Dependencies

Azure Cognitive Services - OCR processing
OpenAI API - VLM analysis and semantic chunking
Django Backend - Database operations
AWS S3 - File storage
Custom Rubric API - Automated rubric generation

Webhook Support
Services support webhook notifications for:

OCR completion
Stamp detection results
Semantic chunking completion
Error notifications

📚 Documentation
For detailed API documentation:

Visit individual service endpoints for OpenAPI specs
Check /health endpoints for service-specific information
Review /config endpoints for current settings

🐛 Troubleshooting
Common Issues

Service Won't Start

Check environment variables are set
Verify Python dependencies installed
Ensure ports 5111 and 5015 are available


External API Errors

Validate API keys and endpoints
Check network connectivity
Review service health endpoints


File Processing Issues

Verify S3 bucket permissions
Check temporary directory write permissions
Validate file format support



Debug Endpoints
bash# VLM Service Debug
GET /apils/vlm/debug/s3/<uuid>

# Webhook Configuration
GET /chunker/debug/webhook-config

# Django API Connection
GET /ocr/test-django
GET /chunker/test-django-connection
📋 Development Roadmap

 Enhanced error handling and retry mechanisms
 Performance optimization for large file processing
 Additional AI model integrations
 Real-time processing status updates
 Batch processing capabilities
 Advanced analytics and reporting
