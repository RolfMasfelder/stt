FROM python:3.12-slim-bookworm

# Set working directory
WORKDIR /app

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash stt && \
    chown -R stt:stt /app
USER stt

# Expose port for potential API
EXPOSE 8000

# Default command
CMD ["python", "transkribe.py"]
