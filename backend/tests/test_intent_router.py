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

    # ── NEW: natural test/performance phrasings ───────────────
    def test_sql_how_i_performed_recent_test(self):
        """User's actual message that was misrouted to RAG."""
        assert detect_intent("how i performed my recent test") == "sql"

    def test_sql_recent_test(self):
        assert detect_intent("show me my recent test") == "sql"

    def test_sql_last_test(self):
        assert detect_intent("how did i do in my last test?") == "sql"

    def test_sql_my_test(self):
        assert detect_intent("what happened in my test?") == "sql"

    def test_sql_how_i_did(self):
        assert detect_intent("how i did in the quiz") == "sql"

    def test_sql_did_i_pass(self):
        assert detect_intent("did i pass the quiz?") == "sql"

    def test_sql_did_i_fail(self):
        assert detect_intent("did i fail?") == "sql"

    def test_sql_marks(self):
        assert detect_intent("what are my marks?") == "sql"

    def test_sql_rank(self):
        assert detect_intent("what is my rank?") == "sql"

    def test_sql_my_stats(self):
        assert detect_intent("show my stats") == "sql"

    def test_sql_quiz_history(self):
        assert detect_intent("show my quiz history") == "sql"

    def test_sql_test_history(self):
        assert detect_intent("my test history") == "sql"

    def test_sql_recent_quiz(self):
        assert detect_intent("my recent quiz results") == "sql"

    def test_sql_perform_variant(self):
        assert detect_intent("how did i perform in my test") == "sql"

    def test_sql_tamil_style_english(self):
        """Common phrasing from Tamil-English users."""
        assert detect_intent("how i performed in test") == "sql"

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

    def test_case_insensitive_recent_test(self):
        assert detect_intent("HOW I PERFORMED MY RECENT TEST") == "sql"

    # ── Edge cases ────────────────────────────────────────────
    def test_empty_string_defaults_rag(self):
        assert detect_intent("") == "rag"

    def test_single_word(self):
        assert detect_intent("python") == "rag"
