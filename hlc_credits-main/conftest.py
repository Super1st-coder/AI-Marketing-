"""Pytest bootstrap.

Makes the hlc_credits root importable (so `from lucas...` / `from app...` resolve) and
pins the test environment BEFORE any app module imports its settings:
- DATABASE_URL -> a shared in-memory SQLite (no Postgres needed to run the suite)
- LUCA_CREDITS_INTERNAL_KEY -> a known value so the API auth tests can send it
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("LUCA_CREDITS_INTERNAL_KEY", "test-internal-key")
