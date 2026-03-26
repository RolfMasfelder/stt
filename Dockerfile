FROM python:3.13-slim-bookworm

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

# Pre-download pyannote model if HF token is available at build time
ARG HF_STT_TOKEN
RUN if [ -n "$HF_STT_TOKEN" ]; then \
    python -c "from pyannote.audio import Pipeline; Pipeline.from_pretrained('pyannote/speaker-diarization-3.1', token='$HF_STT_TOKEN')" \
    && echo "pyannote model cached"; \
    fi

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash stt && \
    chown -R stt:stt /app /home/stt
USER stt

# Default command
CMD ["python", "-m", "stt"]
