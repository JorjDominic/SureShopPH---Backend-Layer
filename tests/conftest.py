"""Pytest configuration. Sets required env BEFORE any app module is imported,
so config.validate_env() (called in lifespan) and the Supabase client init
won't fail on missing values during unit tests.
"""
import os

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-service-role-key")
os.environ.setdefault("JWT_SECRET", "test-secret-for-unit-tests-only-32chars!")
os.environ.setdefault("LOG_LEVEL", "WARNING")
