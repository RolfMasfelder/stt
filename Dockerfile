# ---- Base stage: shared system dependencies and Python packages ----
FROM python:3.13-slim-bookworm AS base

WORKDIR /app

# Install system dependencies for audio processing (ffmpeg for format conversion)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

ENV PYTHONPATH=/app/src

# ---- Production stage: minimal image for deployment ----
FROM base AS production

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash stt && \
    chown -R stt:stt /app /home/stt
USER stt

CMD ["python", "-m", "gunicorn", "stt.wsgi:application", "--bind", "0.0.0.0:8090", "--workers", "2", "--timeout", "600"]

# ---- Dev/Test stage: includes pytest, ruff, bandit etc. ----
FROM base AS dev

COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash stt && \
    chown -R stt:stt /app /home/stt
USER stt

CMD ["python", "-m", "pytest", "tests/", "-x", "-q"]
