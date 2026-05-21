"""
Regression Tests — Quiz Generator Service
Tests _extract_json_array robustness for various LLM response formats.
Run: pytest backend/tests/test_quiz_generator.py -v
"""
import sys
import os
import types

# ── Stub heavy dependencies ────────────────────────────────────
for _name in ["httpx", "fastapi", "sqlalchemy", "sqlalchemy.orm", "config",
              "db", "db.mysql"]:
    if _name not in sys.modules:
        sys.modules[_name] = types.ModuleType(_name)

sys.modules["config"].settings = types.SimpleNamespace(
    ollama_host="http://localhost:11434",
    llm_model="qwen2.5:7b",
)
# sqlalchemy.orm.Session must be importable
sys.modules["sqlalchemy.orm"].Session = object  # type: ignore
# db.mysql helpers used at module level
sys.modules["db.mysql"].execute = lambda *a, **kw: None  # type: ignore
sys.modules["db.mysql"].fetch_one = lambda *a, **kw: {}  # type: ignore

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.quiz_generator import _extract_json_array, _GENERATE_PROMPT  # noqa: E402


VALID_QUESTION = {
    "question": "Who scored the most runs in IPL history?",
    "answer": "Virat Kohli",
    "type": "open",
    "options": None,
    "difficulty": "medium",
}

VALID_MCQ = {
    "question": "Who leads CSK?",
    "answer": "MS Dhoni",
    "type": "mcq",
    "options": ["MS Dhoni", "Rohit Sharma", "Virat Kohli", "Hardik Pandya"],
    "difficulty": "easy",
}


class TestExtractJsonArray:
    """Validate _extract_json_array handles all LLM output formats."""

    def test_bare_json_array(self):
        """Standard case: LLM returns a clean JSON array."""
        raw = '[{"question": "Q1", "answer": "A1", "type": "open", "options": null, "difficulty": "easy"}]'
        result = _extract_json_array(raw)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["question"] == "Q1"

    def test_array_with_markdown_fence(self):
        """LLM wraps JSON in ```json ... ``` code fence."""
        raw = '```json\n[{"question": "Q1", "answer": "A1"}]\n```'
        result = _extract_json_array(raw)
        assert isinstance(result, list)
        assert len(result) == 1

    def test_array_with_preamble_text(self):
        """LLM adds preamble text before the JSON array."""
        raw = 'Here are the quiz questions:\n\n[{"question": "Q1", "answer": "A1"}]'
        result = _extract_json_array(raw)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["answer"] == "A1"

    def test_wrapped_in_object_with_questions_key(self):
        """LLM wraps array in a JSON object: {"questions": [...]}"""
        import json
        questions = [VALID_QUESTION, VALID_MCQ]
        raw = json.dumps({"questions": questions})
        result = _extract_json_array(raw)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_wrapped_in_object_with_data_key(self):
        """LLM wraps array under a generic key like 'data'."""
        import json
        raw = json.dumps({"data": [VALID_QUESTION]})
        result = _extract_json_array(raw)
        assert isinstance(result, list)
        assert len(result) == 1

    def test_multiple_questions_in_array(self):
        """Multiple questions extracted correctly."""
        import json
        raw = json.dumps([VALID_QUESTION, VALID_MCQ])
        result = _extract_json_array(raw)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_empty_array(self):
        """Empty array returns empty list."""
        result = _extract_json_array("[]")
        assert result == []

    def test_no_json_returns_empty_list(self):
        """Completely invalid response returns empty list instead of raising."""
        result = _extract_json_array("I cannot generate quiz questions from this content.")
        assert result == []

    def test_malformed_json_returns_empty_list(self):
        """Truncated/malformed JSON returns empty list without raising."""
        result = _extract_json_array('[{"question": "Q1", "answer":')
        assert result == []

    def test_empty_string_returns_empty_list(self):
        """Empty string input returns empty list."""
        result = _extract_json_array("")
        assert result == []

    def test_whitespace_only_returns_empty_list(self):
        """Whitespace-only input returns empty list."""
        result = _extract_json_array("   \n\t  ")
        assert result == []

    def test_mcq_options_preserved(self):
        """MCQ options list is preserved correctly through extraction."""
        import json
        raw = json.dumps([VALID_MCQ])
        result = _extract_json_array(raw)
        assert isinstance(result, list)
        assert result[0]["options"] == VALID_MCQ["options"]
        assert len(result[0]["options"]) == 4


class TestGeneratePromptTemplate:
    """Regression: _GENERATE_PROMPT.format() must not raise KeyError.

    Root cause: The prompt contains a JSON example block with literal { } braces
    which Python's str.format() was misinterpreting as unnamed format placeholders,
    causing KeyError: '\n  "question"'.
    Fix: Escape literal braces in the template as {{ and }}.
    """

    def test_format_with_content_does_not_raise(self):
        """Formatting with any content must not throw KeyError."""
        try:
            result = _GENERATE_PROMPT.format(content="Test IPL content about captains.")
        except KeyError as e:
            raise AssertionError(
                f"_GENERATE_PROMPT.format() raised KeyError: {e!r}. "
                "Ensure all literal curly braces in the template are escaped as {{ and }}."
            ) from e
        assert "{content}" not in result, "Placeholder must be replaced"
        assert "Test IPL content about captains." in result

    def test_format_result_contains_json_example_braces(self):
        """After formatting, the JSON example block should still contain { and } (unescaped)."""
        result = _GENERATE_PROMPT.format(content="dummy")
        assert "{" in result, "Formatted prompt should contain literal { for JSON example"
        assert "}" in result, "Formatted prompt should contain literal } for JSON example"

    def test_format_with_special_characters_in_content(self):
        """Content with special characters (braces, quotes) must not break formatting."""
        content = 'MS Dhoni {the captain} earned "Captain Cool" nickname.'
        try:
            _GENERATE_PROMPT.format(content=content)
        except (KeyError, ValueError) as e:
            raise AssertionError(f"Unexpected error with special-char content: {e!r}") from e
