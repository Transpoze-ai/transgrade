# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    FLASK_APP=rubric.main:app \
    FLASK_ENV=production \
    PORT=5033 \
    OPENAI_API_KEY=${OPENAI_API_KEY}

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project configuration files first
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir "hatchling>=1.21.0" && \
    pip install --no-cache-dir \
        "crewai[tools]>=0.119.0,<1.0.0" \
        "flask>=3.0.3,<4.0.0" \
        "flask-cors>=4.0.0,<5.0.0" \
        "openai>=1.13.3"

# Copy application code
COPY src/rubric ./rubric

# Create necessary directories
RUN mkdir -p /app/logs /app/data

# Create a non-root user for security
RUN useradd -m -u 1000 crewuser && \
    chown -R crewuser:crewuser /app
USER crewuser

# Expose the port
EXPOSE 5033

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5033/rubric/health || exit 1

# Default command to run the Flask server
CMD ["python", "-m", "rubric.main"]