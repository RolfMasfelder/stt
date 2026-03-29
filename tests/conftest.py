"""Shared pytest configuration for STT tests."""

import os

# Use local PostgreSQL container for tests.
os.environ.setdefault("DATABASE_URL", "postgres://stt:stt_dev@127.0.0.1:5432/stt")
