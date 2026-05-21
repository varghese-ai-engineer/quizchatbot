"""
Pydantic schemas for request / response validation.
"""
from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    full_name: str
    credits: int
    language: str


# ── Chat ──────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    language: str = Field(default="en", pattern="^(en|ta|hi)$")
    user_id: int


# ── Quiz ──────────────────────────────────────────────────────
class QuizStartRequest(BaseModel):
    user_id: int
    topic_slug: str
    language: str = "en"  # en | ta | hi


class QuizAnswerRequest(BaseModel):
    quiz_session_id: int
    question_id: int
    user_answer: str
    language: str = "en"  # en | ta | hi
