"""Shared pytest configuration for STT tests."""

import os

# Use in-memory SQLite for tests (no PostgreSQL needed).
os.environ.setdefault("DATABASE_URL", "sqlite://:memory:")
