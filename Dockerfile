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

# Install the stt package
RUN pip install --no-cache-dir -e .

# Pre-download pyannote model if HF token is available at build time
# Usage: DOCKER_BUILDKIT=1 docker build --secret id=hf_token,env=HF_STT_TOKEN .
RUN --mount=type=secret,id=hf_token \
    HF_STT_TOKEN=$(cat /run/secrets/hf_token 2>/dev/null || true) && \
    if [ -n "$HF_STT_TOKEN" ]; then \
    python -c "from pyannote.audio import Pipeline; \
    Pipeline.from_pretrained('pyannote/speaker-diarization-3.1', \
    token='$HF_STT_TOKEN')" \
    && echo "pyannote model cached"; \
    fi

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash stt && \
    chown -R stt:stt /app /home/stt
USER stt

# Default command: run FastAPI server
CMD ["python", "-m", "uvicorn", "stt.server:app", "--host", "0.0.0.0", "--port", "8090"]
