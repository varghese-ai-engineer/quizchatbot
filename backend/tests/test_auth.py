"""
Regression Tests — Auth Routes
Tests: /api/auth/register and /api/auth/login endpoints.
Run: pytest backend/tests/test_auth.py -v
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from main import app

client = TestClient(app)

# ── Shared fixtures ───────────────────────────────────────────
MOCK_USER = {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "password": "$2b$12$DummyHashedPasswordForTesting1234",
    "full_name": "Test User",
    "credits": 100,
    "language": "en",
    "is_active": 1,
}


class TestRegister:
    """Test suite for /api/auth/register"""

    @patch("routers.auth.fetch_one", return_value=None)
    @patch("routers.auth.execute", return_value=1)
    def test_register_success(self, mock_exec, mock_fetch):
        resp = client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123",
            "full_name": "New User",
        })
        assert resp.status_code == 201
        assert "message" in resp.json()

    @patch("routers.auth.fetch_one", return_value=MOCK_USER)
    def test_register_duplicate_email(self, mock_fetch):
        resp = client.post("/api/auth/register", json={
            "username": "anotheruser",
            "email": "test@example.com",
            "password": "password123",
            "full_name": "Another User",
        })
        assert resp.status_code == 409

    def test_register_missing_fields(self):
        resp = client.post("/api/auth/register", json={
            "email": "incomplete@example.com",
        })
        assert resp.status_code == 422

    def test_register_short_password(self):
        resp = client.post("/api/auth/register", json={
            "username": "user",
            "email": "short@example.com",
            "password": "123",
            "full_name": "Short Pass",
        })
        assert resp.status_code == 422

    def test_register_invalid_email(self):
        resp = client.post("/api/auth/register", json={
            "username": "user2",
            "email": "not-an-email",
            "password": "password123",
            "full_name": "Bad Email",
        })
        assert resp.status_code == 422


class TestLogin:
    """Test suite for /api/auth/login"""

    @patch("routers.auth.fetch_one", return_value=None)
    def test_login_wrong_email(self, mock_fetch):
        resp = client.post("/api/auth/login", json={
            "email": "nobody@example.com",
            "password": "password123",
        })
        assert resp.status_code == 401

    def test_login_invalid_email_format(self):
        resp = client.post("/api/auth/login", json={
            "email": "not-email",
            "password": "password123",
        })
        assert resp.status_code == 422

    def test_login_missing_password(self):
        resp = client.post("/api/auth/login", json={
            "email": "test@example.com",
        })
        assert resp.status_code == 422
