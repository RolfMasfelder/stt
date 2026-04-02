# ---- ML Service: FastAPI + torch/pyannote/faster-whisper ----
FROM python:3.13-slim-bookworm

WORKDIR /app

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install PyTorch CPU first, then remaining dependencies
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.11.0+cpu torchaudio==2.11.0+cpu torchcodec==0.11.0 && \
    pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Pre-download pyannote model if HF token is available at build time
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

EXPOSE 8091

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8091"]
