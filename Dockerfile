# ---- Base stage: shared system dependencies and Python packages ----
FROM python:3.14-slim-bookworm AS base

WORKDIR /app

# Install system dependencies for audio processing (ffmpeg for format conversion)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# ---- Production stage: minimal image for deployment ----
FROM base AS production

# Install package without dev dependencies
RUN pip install --no-cache-dir -e .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash stt && \
    chown -R stt:stt /app /home/stt
USER stt

CMD ["python", "-m", "gunicorn", "stt.wsgi:application", "--bind", "0.0.0.0:8090", "--workers", "2", "--timeout", "600"]

# ---- Dev/Test stage: includes pytest, ruff, bandit etc. ----
FROM base AS dev

# Install package with dev/test dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash stt && \
    chown -R stt:stt /app /home/stt
USER stt

CMD ["python", "-m", "pytest", "tests/", "-x", "-q"]
