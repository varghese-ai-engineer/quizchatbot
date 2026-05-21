"""
Regression Tests — Intent Router
Tests: detect_intent() with various message inputs.
Run: pytest backend/tests/test_intent_router.py -v
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.intent_router import detect_intent


class TestIntentRouter:
    """Test suite for intent detection."""

    # ── RAG intent ────────────────────────────────────────────
    def test_rag_python_question(self):
        assert detect_intent("What is Python list comprehension?") == "rag"

    def test_rag_ml_question(self):
        assert detect_intent("Explain supervised learning") == "rag"

    def test_rag_generic_question(self):
        assert detect_intent("What is a binary tree?") == "rag"

    def test_rag_definition(self):
        assert detect_intent("Define recursion in programming") == "rag"

    # ── SQL / Scores intent ───────────────────────────────────
    def test_sql_last_quiz(self):
        assert detect_intent("How did I do in my last quiz?") == "sql"

    def test_sql_score(self):
        assert detect_intent("What was my score?") == "sql"

    def test_sql_performance(self):
        assert detect_intent("Show my performance this week") == "sql"

    def test_sql_progress(self):
        assert detect_intent("What is my progress so far?") == "sql"

    def test_sql_credits(self):
        assert detect_intent("How many credits do I have left?") == "sql"

    # ── Quiz intent ───────────────────────────────────────────
    def test_quiz_start(self):
        assert detect_intent("Test my Python skills") == "quiz"

    def test_quiz_explicit(self):
        assert detect_intent("Start a quiz on machine learning") == "quiz"

    def test_quiz_me(self):
        assert detect_intent("Quiz me on data structures") == "quiz"

    def test_quiz_practice(self):
        assert detect_intent("I want to practice Python") == "quiz"

    def test_quiz_exam(self):
        assert detect_intent("Give me an exam") == "quiz"

    # ── Case insensitivity ────────────────────────────────────
    def test_case_insensitive_quiz(self):
        assert detect_intent("QUIZ ME ON PYTHON") == "quiz"

    def test_case_insensitive_score(self):
        assert detect_intent("MY SCORE IN LAST QUIZ") == "sql"

    # ── Edge cases ────────────────────────────────────────────
    def test_empty_string_defaults_rag(self):
        assert detect_intent("") == "rag"

    def test_single_word(self):
        assert detect_intent("python") == "rag"
