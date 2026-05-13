"""Unit tests for JWT verification and role helpers."""
import time

import jwt

from app.auth import is_admin, verify_token
from app.config import JWT_SECRET


def _token(payload: dict, secret: str = JWT_SECRET) -> str:
    return jwt.encode(payload, secret, algorithm="HS256")


def test_valid_token_returns_sub():
    token = _token({"sub": "user-abc", "exp": int(time.time()) + 3600})
    assert verify_token(token) == "user-abc"


def test_expired_token_returns_none():
    token = _token({"sub": "user-abc", "exp": int(time.time()) - 1})
    assert verify_token(token) is None


def test_wrong_secret_returns_none():
    token = _token(
        {"sub": "user-abc", "exp": int(time.time()) + 3600},
        secret="wrong-secret-value-with-at-least-32-bytes",
    )
    assert verify_token(token) is None


def test_malformed_token_returns_none():
    assert verify_token("not.a.jwt") is None
    assert verify_token("") is None


def test_is_admin_true():
    assert is_admin({"role": "admin"}) is True


def test_is_admin_false():
    assert is_admin({"role": "user"}) is False
    assert is_admin({}) is False
    assert is_admin(None) is False
