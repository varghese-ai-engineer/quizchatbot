"""
Unit Tests for LLM Feedback Sanitizer
Validates that _sanitize_feedback correctly post-processes LLM evaluation responses
for Tamil, Hindi, and English, stripping contradictory status words and ensuring
a consistent status prefix.
"""
import sys
import os
import types

# ── Stub heavy dependencies so we can import the module without a running stack ──
for _name in [
    "fastapi", "sqlalchemy", "sqlalchemy.orm", "httpx",
    "config", "db", "db.mysql", "models", "models.schemas",
]:
    if _name not in sys.modules:
        sys.modules[_name] = types.ModuleType(_name)

# Provide stub attributes used at import time
sys.modules["fastapi"].APIRouter = lambda: types.SimpleNamespace(
    get=lambda *a, **kw: (lambda f: f),
    post=lambda *a, **kw: (lambda f: f),
)
sys.modules["fastapi"].Depends = lambda x: x
sys.modules["fastapi"].HTTPException = Exception
sys.modules["sqlalchemy.orm"].Session = object
sys.modules["db.mysql"].execute = lambda *a, **kw: None
sys.modules["db.mysql"].fetch_all = lambda *a, **kw: []
sys.modules["db.mysql"].fetch_one = lambda *a, **kw: {}
sys.modules["db.mysql"].get_db = lambda: None
sys.modules["models.schemas"].QuizAnswerRequest = object
sys.modules["models.schemas"].QuizStartRequest = object
sys.modules["config"].settings = types.SimpleNamespace(ollama_host="", llm_model="")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from routers.quiz import _sanitize_feedback  # noqa: E402


class TestTamilFeedbackSanitization:
    """Validate Tamil feedback sanitization."""

    def test_correct_verdict_strips_wrong_and_prepends_correct(self):
        # Case 1: Contradictory "சரியான தவறை!" on correct answer
        raw = "சரியான தவறை! Yashasvi Jaiswal தான் IPL-ல் மிக விழுதமாக 50-run அடித்துள்ளார்."
        result = _sanitize_feedback(raw, is_correct=True, language="ta")
        assert result.startswith("சரி! ")
        assert "Yashasvi Jaiswal தான்" in result
        assert "தவற" not in result.split("!")[0]  # First part should not contain wrong words

        # Case 2: Starts with wrong prefix "தவறு." but is correct
        raw2 = "தவறு. Yashasvi Jaiswal தான் IPL-ல் 50 அடிச்சாரு."
        result2 = _sanitize_feedback(raw2, is_correct=True, language="ta")
        assert result2.startswith("சரி! ")
        assert "Yashasvi Jaiswal" in result2
        assert "தவறு" not in result2

        # Case 3: Does not start with "சரி" or "தவறு"
        raw3 = "Yashasvi Jaiswal தான் IPL-ல் 50 அடிச்சாரு."
        result3 = _sanitize_feedback(raw3, is_correct=True, language="ta")
        assert result3 == "சரி! Yashasvi Jaiswal தான் IPL-ல் 50 அடிச்சாரு."

        # Case 4: Already starts with "சரி!"
        raw4 = "சரி! Yashasvi Jaiswal தான் fastest 50."
        result4 = _sanitize_feedback(raw4, is_correct=True, language="ta")
        assert result4 == raw4

    def test_incorrect_verdict_strips_correct_and_prepends_wrong(self):
        # Case 1: Starts with "சரி!" but is incorrect
        raw = "சரி! correct answer Yashasvi Jaiswal, Virat Kohli இல்லை."
        result = _sanitize_feedback(raw, is_correct=False, language="ta")
        assert result.startswith("தவறு. ")
        assert "சரி" not in result.split(".")[0]

        # Case 2: Starts with "சரியான பதில்" (Correct answer) but is incorrect
        raw2 = "சரியான பதில் Yashasvi Jaiswal, Virat Kohli இல்லை."
        result2 = _sanitize_feedback(raw2, is_correct=False, language="ta")
        assert result2.startswith("தவறு. ")
        assert "சரியான பதில்" not in result2

        # Case 3: Does not start with either
        raw3 = "Yashasvi Jaiswal, Virat Kohli இல்லை."
        result3 = _sanitize_feedback(raw3, is_correct=False, language="ta")
        assert result3 == "தவறு. Yashasvi Jaiswal, Virat Kohli இல்லை."


class TestHindiFeedbackSanitization:
    """Validate Hindi feedback sanitization."""

    def test_correct_verdict_strips_wrong_and_prepends_correct(self):
        # Case 1: Starts with wrong prefix "गलत" but is correct
        raw = "गलत. Yashasvi Jaiswal ने fastest 50 मारा।"
        result = _sanitize_feedback(raw, is_correct=True, language="hi")
        assert result.startswith("सही! ")
        assert "गलत" not in result

        # Case 2: Already correct
        raw2 = "सही! Yashasvi Jaiswal ने मारा।"
        assert _sanitize_feedback(raw2, is_correct=True, language="hi") == raw2

    def test_incorrect_verdict_strips_correct_and_prepends_wrong(self):
        # Case 1: Starts with "सही" but is incorrect
        raw = "सही! सही answer Yashasvi Jaiswal है।"
        result = _sanitize_feedback(raw, is_correct=False, language="hi")
        assert result.startswith("गलत. ")


class TestEnglishFeedbackSanitization:
    """Validate English feedback sanitization."""

    def test_correct_verdict_strips_wrong_and_prepends_correct(self):
        # Case 1: Incorrect prefix on correct answer
        raw = "Incorrect. Yashasvi Jaiswal is correct."
        result = _sanitize_feedback(raw, is_correct=True, language="en")
        assert result.startswith("Correct! ")
        assert "Incorrect" not in result

        # Case 2: Wrong prefix on correct answer
        raw2 = "wrong! Yashasvi Jaiswal is correct."
        result2 = _sanitize_feedback(raw2, is_correct=True, language="en")
        assert result2.startswith("Correct! ")
        assert "wrong" not in result2.lower()

    def test_incorrect_verdict_strips_correct_and_prepends_wrong(self):
        # Case 1: Correct prefix on incorrect answer
        raw = "Correct! The answer is Yashasvi Jaiswal."
        result = _sanitize_feedback(raw, is_correct=False, language="en")
        assert result.startswith("Incorrect. ")
        assert "Correct" not in result
