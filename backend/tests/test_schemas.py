"""
Regression Tests — Chat Schemas
Tests: Pydantic schema validation for ChatRequest.
Run: pytest backend/tests/test_schemas.py -v
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pydantic import ValidationError
from models.schemas import ChatRequest, RegisterRequest, QuizStartRequest


class TestChatRequestSchema:
    """Test ChatRequest validation."""

    def test_valid_chat_request(self):
        req = ChatRequest(message="Hello", language="en", user_id=1)
        assert req.message == "Hello"
        assert req.language == "en"

    def test_valid_tamil_language(self):
        req = ChatRequest(message="வணக்கம்", language="ta", user_id=1)
        assert req.language == "ta"

    def test_valid_hindi_language(self):
        req = ChatRequest(message="नमस्ते", language="hi", user_id=1)
        assert req.language == "hi"

    def test_invalid_language(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="Hello", language="fr", user_id=1)

    def test_empty_message_rejected(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="", language="en", user_id=1)

    def test_message_too_long(self):
        with pytest.raises(ValidationError):
            ChatRequest(message="x" * 2001, language="en", user_id=1)

    def test_default_language_is_english(self):
        req = ChatRequest(message="Test", user_id=1)
        assert req.language == "en"


class TestRegisterSchema:
    """Test RegisterRequest validation."""

    def test_valid_register(self):
        req = RegisterRequest(
            username="alice",
            email="alice@example.com",
            password="secure123",
            full_name="Alice Smith",
        )
        assert req.username == "alice"

    def test_username_too_short(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                username="ab",
                email="ab@example.com",
                password="password",
                full_name="AB",
            )

    def test_password_too_short(self):
        with pytest.raises(ValidationError):
            RegisterRequest(
                username="validuser",
                email="user@example.com",
                password="12345",
                full_name="Valid User",
            )


class TestQuizStartSchema:
    """Test QuizStartRequest validation."""

    def test_valid_quiz_start(self):
        req = QuizStartRequest(user_id=1, topic_slug="python-basics")
        assert req.topic_slug == "python-basics"

    def test_missing_topic_slug(self):
        with pytest.raises(ValidationError):
            QuizStartRequest(user_id=1)
