"""
Regression Tests — MCQ Language-Aware Feedback Strings
Validates that quiz evaluation feedback is correctly localised for each UI language
and never mixes English feedback phrases (e.g. "Correct!") into Tamil/Hindi responses.

Run: pytest backend/tests/test_mcq_feedback.py -v
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

from routers.quiz import _MCQ_CORRECT, _MCQ_INCORRECT  # noqa: E402

SUPPORTED_LANGUAGES = ["en", "ta", "hi"]


class TestMcqCorrectStrings:
    """_MCQ_CORRECT must exist for every supported language and not be empty."""

    def test_all_languages_have_correct_string(self):
        for lang in SUPPORTED_LANGUAGES:
            assert lang in _MCQ_CORRECT, f"Missing _MCQ_CORRECT entry for lang='{lang}'"

    def test_no_correct_string_is_empty(self):
        for lang, msg in _MCQ_CORRECT.items():
            assert msg.strip(), f"_MCQ_CORRECT['{lang}'] must not be blank"

    def test_tamil_correct_is_not_english_correct(self):
        """The Tamil feedback must not be the English word 'Correct!'."""
        assert _MCQ_CORRECT["ta"] != "Correct!", \
            "Tamil MCQ correct feedback must be in Tamil, not English 'Correct!'"

    def test_hindi_correct_is_not_english_correct(self):
        assert _MCQ_CORRECT["hi"] != "Correct!", \
            "Hindi MCQ correct feedback must be in Hindi, not English 'Correct!'"

    def test_english_correct_contains_correct_word(self):
        assert "Correct" in _MCQ_CORRECT["en"]


class TestMcqIncorrectStrings:
    """_MCQ_INCORRECT must exist for every language and support {answer} substitution."""

    def test_all_languages_have_incorrect_string(self):
        for lang in SUPPORTED_LANGUAGES:
            assert lang in _MCQ_INCORRECT, f"Missing _MCQ_INCORRECT entry for lang='{lang}'"

    def test_all_incorrect_strings_have_answer_placeholder(self):
        for lang, template in _MCQ_INCORRECT.items():
            assert "{answer}" in template, \
                f"_MCQ_INCORRECT['{lang}'] must contain '{{answer}}' placeholder"

    def test_tamil_incorrect_formats_correctly(self):
        result = _MCQ_INCORRECT["ta"].format(answer="MS Dhoni")
        assert "MS Dhoni" in result, "Formatted Tamil incorrect string must include the answer"
        assert "Incorrect" not in result, \
            "Tamil incorrect feedback must not contain the English word 'Incorrect'"

    def test_hindi_incorrect_formats_correctly(self):
        result = _MCQ_INCORRECT["hi"].format(answer="CSK")
        assert "CSK" in result, "Formatted Hindi incorrect string must include the answer"
        assert "Incorrect" not in result, \
            "Hindi incorrect feedback must not contain the English word 'Incorrect'"

    def test_english_incorrect_formats_correctly(self):
        result = _MCQ_INCORRECT["en"].format(answer="MS Dhoni")
        assert "MS Dhoni" in result
        assert "Incorrect" in result


class TestMcqFeedbackLookup:
    """Simulate the submit_answer language-selection logic."""

    def _get_feedback(self, language: str, is_correct: bool, correct_answer: str) -> str:
        lang = language if language in _MCQ_CORRECT else "en"
        if is_correct:
            return _MCQ_CORRECT[lang]
        return _MCQ_INCORRECT[lang].format(answer=correct_answer)

    def test_english_correct(self):
        fb = self._get_feedback("en", True, "MS Dhoni")
        assert "Correct" in fb

    def test_tamil_correct_not_english(self):
        fb = self._get_feedback("ta", True, "MS Dhoni")
        assert "Correct!" != fb, "Tamil correct feedback must not be English 'Correct!'"

    def test_hindi_correct_not_english(self):
        fb = self._get_feedback("hi", True, "MS Dhoni")
        assert "Correct!" != fb

    def test_tamil_incorrect_includes_answer(self):
        fb = self._get_feedback("ta", False, "Yashasvi Jaiswal")
        assert "Yashasvi Jaiswal" in fb

    def test_hindi_incorrect_includes_answer(self):
        fb = self._get_feedback("hi", False, "CSK")
        assert "CSK" in fb

    def test_unknown_language_falls_back_to_english(self):
        """An unknown language code must fall back to 'en'."""
        fb_correct   = self._get_feedback("zz", True,  "MS Dhoni")
        fb_incorrect = self._get_feedback("zz", False, "MS Dhoni")
        assert fb_correct   == _MCQ_CORRECT["en"]
        assert fb_incorrect == _MCQ_INCORRECT["en"].format(answer="MS Dhoni")
