# Multi-stage Dockerfile for IRS Tax Form Parser
# Production-ready container with optimized layers

# Stage 1: Base dependencies and system packages
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Tesseract OCR and language packs
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    # Image processing libraries
    libpoppler-cpp-dev \
    libpoppler-utils \
    poppler-utils \
    # OpenCV dependencies
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    # System utilities
    wget \
    curl \
    git \
    build-essential \
    pkg-config \
    # Database clients
    postgresql-client \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --user-group taxparser
USER taxparser
WORKDIR /home/taxparser

# Stage 2: Python dependencies
FROM base as dependencies

# Switch to root for pip install
USER root

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Switch back to non-root user
USER taxparser

# Stage 3: Application
FROM dependencies as application

# Copy application code
COPY --chown=taxparser:taxparser . /home/taxparser/app
WORKDIR /home/taxparser/app

# Create necessary directories
RUN mkdir -p /home/taxparser/app/output \
             /home/taxparser/app/logs \
             /home/taxparser/app/uploads \
             /home/taxparser/app/temp

# Set Python path
ENV PYTHONPATH="${PYTHONPATH}:/home/taxparser/app"

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD python -c "import src.main; print('Health check passed')" || exit 1

# Expose port (if running as web service)
EXPOSE 8000

# Default command
CMD ["python", "-m", "src.main", "--help"]

# Stage 4: Development environment (optional)
FROM application as development

USER root

# Install development tools
RUN pip install --no-cache-dir \
    pytest \
    pytest-cov \
    black \
    flake8 \
    mypy \
    pre-commit \
    jupyter \
    ipykernel

USER taxparser

# Development-specific environment variables
ENV ENVIRONMENT=development \
    LOG_LEVEL=DEBUG

CMD ["/bin/bash"]

# Stage 5: Production environment
FROM application as production

# Production environment variables
ENV ENVIRONMENT=production \
    LOG_LEVEL=INFO \
    WORKERS=4

# Optimize Python
ENV PYTHONOPTIMIZE=1

# Production command (adjust based on your deployment needs)
CMD ["python", "-m", "src.main"]