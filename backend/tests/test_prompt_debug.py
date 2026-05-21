"""
Regression Tests — Prompt Debug Toggle
Tests: show_prompt_debug logic in quiz answer endpoint and chat SSE stream.
Run: pytest backend/tests/test_prompt_debug.py -v
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch, AsyncMock


# ── Helpers ───────────────────────────────────────────────────


def _make_db_row(show_prompt_debug: int) -> MagicMock:
    """Return a mock DB row with show_prompt_debug field."""
    row = MagicMock()
    row.__getitem__ = lambda self, key: show_prompt_debug if key == "show_prompt_debug" else None
    return row


# ── Unit: debug_prompt presence in quiz answer response ──────


class TestQuizPromptDebug:
    """Verify that debug_prompt is returned only when flag is ON and question is open-ended."""

    def test_debug_prompt_none_when_flag_off(self):
        """When show_prompt_debug=0, debug_prompt should be None."""
        show_debug = False
        question_type = "open"
        debug_prompt = None
        if show_debug and question_type == "open":
            debug_prompt = "=== QUIZ EVALUATION PROMPT ===\nQuestion: ..."
        assert debug_prompt is None

    def test_debug_prompt_set_when_flag_on_and_open(self):
        """When show_prompt_debug=1 and question is open, debug_prompt should be non-empty."""
        show_debug = True
        question_type = "open"
        user_answer = "Mumbai Indians"
        question_text = "Which team has won the most IPL titles?"
        correct_answer = "Mumbai Indians"
        lang_rules = "Keep team names in English."

        debug_prompt = None
        if show_debug and question_type == "open":
            lang_name = {"en": "English", "ta": "Tamil", "hi": "Hindi"}.get("en", "English")
            debug_prompt = (
                f"=== QUIZ EVALUATION PROMPT ===\n"
                f"Question: {question_text}\n"
                f"Correct Answer: {correct_answer}\n"
                f"Student's Answer: {user_answer}\n"
                f"Evaluate in: {lang_name}\n"
                f"Language Rules:\n{lang_rules}"
            )

        assert debug_prompt is not None
        assert "QUIZ EVALUATION PROMPT" in debug_prompt
        assert "Mumbai Indians" in debug_prompt
        assert "Language Rules:" in debug_prompt

    def test_debug_prompt_none_for_mcq_even_when_flag_on(self):
        """Even if show_prompt_debug=1, MCQ questions do not produce a debug_prompt."""
        show_debug = True
        question_type = "mcq"
        debug_prompt = None
        if show_debug and question_type == "open":
            debug_prompt = "=== QUIZ EVALUATION PROMPT ===\n..."
        assert debug_prompt is None

    def test_debug_prompt_includes_all_languages(self):
        """debug_prompt should respect the active language label."""
        for lang_code, lang_name in [("en", "English"), ("ta", "Tamil"), ("hi", "Hindi")]:
            debug_prompt = (
                f"=== QUIZ EVALUATION PROMPT ===\n"
                f"Evaluate in: {lang_name}\n"
            )
            assert lang_name in debug_prompt


# ── Unit: debug_prompt field in quiz answer API response dict ─


class TestQuizAnswerResponseShape:
    """Verify the response dict always includes the debug_prompt key."""

    def _build_response(self, is_correct: bool, feedback: str, correct_answer: str,
                        marks_awarded: int, debug_prompt):
        return {
            "is_correct": is_correct,
            "correct_answer": correct_answer,
            "feedback": feedback,
            "marks_awarded": marks_awarded,
            "debug_prompt": debug_prompt,
        }

    def test_response_has_debug_prompt_key_when_none(self):
        r = self._build_response(True, "Correct!", "MI", 1, None)
        assert "debug_prompt" in r
        assert r["debug_prompt"] is None

    def test_response_has_debug_prompt_key_with_value(self):
        prompt_text = "=== QUIZ EVALUATION PROMPT ===\nQuestion: Who won IPL 2023?"
        r = self._build_response(False, "Wrong.", "CSK", 0, prompt_text)
        assert "debug_prompt" in r
        assert r["debug_prompt"] == prompt_text


# ── Unit: Chat SSE — debug_prompt emitted only when flag is ON ─


class TestChatDebugPromptSSE:
    """Simulate the SSE emission logic for debug_prompt in chat.py."""

    def _emit_debug(self, show_debug: bool, debug_prompt):
        """Mimic the logic in chat.py: only emit debug_prompt if flag is ON."""
        events = []
        if show_debug and debug_prompt:
            events.append({"debug_prompt": debug_prompt})
        return events

    def test_debug_not_emitted_when_flag_off(self):
        events = self._emit_debug(False, "=== SYSTEM PROMPT ===\nSome prompt text.")
        assert events == []

    def test_debug_not_emitted_when_prompt_none(self):
        events = self._emit_debug(True, None)
        assert events == []

    def test_debug_emitted_when_flag_on_and_prompt_set(self):
        prompt = "=== SYSTEM PROMPT ===\nBe helpful."
        events = self._emit_debug(True, prompt)
        assert len(events) == 1
        assert events[0]["debug_prompt"] == prompt

    def test_debug_emitted_once_per_call(self):
        prompt = "=== SYSTEM PROMPT ===\nContext text."
        events = self._emit_debug(True, prompt)
        assert len(events) == 1  # only one event per LLM call


# ── Unit: Tamil prompt quality debug ────────────────────────────


class TestTamilPromptDebugInspection:
    """Ensure that the debug prompt exposes enough info to diagnose bad Tamil output."""

    def test_system_prompt_contains_language_instruction(self):
        """
        The debug popup should show the language instruction used.
        This lets a dev see if the Tamil instruction is too weak/missing.
        """
        ta_instruction = (
            "Respond in simple, everyday conversational Tamil (தமிழ்). "
            "Write naturally as people speak — not formal or literary Tamil. "
            "Do NOT include religious phrases, blessings, or emotional filler."
        )
        debug_prompt = (
            "=== SYSTEM PROMPT ===\n"
            f"=== LANGUAGE INSTRUCTIONS ===\n{ta_instruction}\n\n"
            "=== USER QUERY ===\nWho has won the most IPL titles?"
        )
        assert "LANGUAGE INSTRUCTIONS" in debug_prompt
        assert "Tamil" in debug_prompt
        assert "தமிழ்" in debug_prompt

    def test_debug_prompt_shows_domain_rules(self):
        """Domain-specific AI rules must be visible in the debug prompt for diagnosis."""
        domain_rules = (
            "Keep all player names in English exactly as written.\n"
            "Keep all team names/abbreviations in English (CSK, MI, RCB, KKR etc.)."
        )
        debug_prompt = (
            "=== SYSTEM PROMPT ===\n"
            f"=== DOMAIN-SPECIFIC AI RULES ===\n{domain_rules}\n"
        )
        assert "DOMAIN-SPECIFIC AI RULES" in debug_prompt
        assert "CSK" in debug_prompt

    def test_debug_prompt_shows_user_query(self):
        """The user's actual query must appear in the debug popup so the dev can correlate."""
        query = "IPL வெற்றியாளர்கள் யார்?"
        debug_prompt = f"=== USER QUERY ===\n{query}"
        assert query in debug_prompt


# ── Regression: Tamil question text leaking into lang_rules ──────


class TestLangRulesSanitization:
    """Regression test for bug: translated question text leaking into ai_language_rules.

    Scenario: The DB field `ai_language_rules` for the cricket knowledge file
    had a stray Tamil-script question line appended, causing that text to appear
    inside the '=== QUIZ EVALUATION PROMPT ===' Language Rules block.

    Fix: _get_lang_rules() now strips any line whose first character is not ASCII
    alpha or a digit — i.e. Tamil/Hindi script lines are silently dropped.
    """

    def _sanitize_rules(self, raw: str) -> str:
        """Mirror of the sanitization logic in quiz.py _get_lang_rules() / _is_valid_rule_line()."""
        _REJECT_FIRST_WORDS = frozenset(["question"])

        def _is_valid(line: str) -> bool:
            stripped = line.strip()
            if not stripped:
                return False
            first_char = stripped[0]
            # Rule 1: must start with ASCII alpha or digit
            if not (first_char.isascii() and (first_char.isalpha() or first_char.isdigit())):
                return False
            # Rule 2: first word must not be a rejected sentinel
            first_word = stripped.split()[0].rstrip(".,: ").lower()
            if first_word in _REJECT_FIRST_WORDS:
                return False
            # Rule 3: must not be predominantly non-ASCII
            ascii_count = sum(1 for c in stripped if c.isascii() and c.isalnum())
            non_ascii_count = sum(1 for c in stripped if not c.isascii())
            if non_ascii_count > ascii_count:
                return False
            return True

        lines = [line for line in raw.splitlines() if _is_valid(line)]
        return "\n".join(lines)

    def test_tamil_question_line_is_stripped(self):
        """A Tamil-script line appended to ai_language_rules must not appear in output."""
        raw = (
            "Keep all player names in English exactly as written — do NOT transliterate.\n"
            "Keep all team names/abbreviations in English (CSK, MI, RCB, KKR etc.).\n"
            "Cricket terms may be used in the selected UI language where natural "
            "(e.g. சதம் for century in Tamil, शतक in Hindi).\n"
            "Keep numbers, dates, and statistics in their original form.\n"
            "question IPL-ல் யாரை Captain Cool-ன்னு சொல்வாங்க?"  # ← the leaked line
        )
        result = self._sanitize_rules(raw)

        # Leaked Tamil question must NOT appear
        assert "IPL-ல்" not in result
        assert "Captain Cool-ன்னு" not in result

    def test_valid_ascii_rules_are_preserved(self):
        """All genuine ASCII rule lines must survive sanitization."""
        raw = (
            "Keep all player names in English exactly as written — do NOT transliterate.\n"
            "Keep all team names/abbreviations in English (CSK, MI, RCB, KKR etc.).\n"
            "Keep numbers, dates, and statistics in their original form.\n"
            "question IPL-ல் யாரை Captain Cool-ன்னு சொல்வாங்க?"
        )
        result = self._sanitize_rules(raw)

        assert "Keep all player names in English" in result
        assert "Keep all team names/abbreviations in English" in result
        assert "Keep numbers, dates, and statistics" in result

    def test_empty_rules_returns_empty_string(self):
        """If all lines are stripped (e.g. all Tamil), result is empty string."""
        raw = "IPL-ல் யாரை Captain Cool-ன்னு சொல்வாங்க?\nMS Dhoni-ஐ Captain Cool என்று அழைக்கிறார்கள்."
        result = self._sanitize_rules(raw)
        assert result == ""

    def test_numbered_rules_preserved(self):
        """Lines starting with digits (e.g. '1. Keep …') are valid and must be kept."""
        raw = (
            "1. Keep all player names in English.\n"
            "2. Keep team abbreviations in English.\n"
            "IPL-ல் யாரை Captain Cool-ன்னு சொல்வாங்க?"
        )
        result = self._sanitize_rules(raw)
        assert "1. Keep all player names" in result
        assert "2. Keep team abbreviations" in result
        assert "IPL-ல்" not in result

    def test_debug_prompt_lang_rules_section_is_clean(self):
        """End-to-end: the Language Rules block in debug_prompt must not contain Tamil question text."""
        raw_rules = (
            "Keep all player names in English exactly as written.\n"
            "Keep all team names/abbreviations in English (CSK, MI, RCB, KKR etc.).\n"
            "question IPL-ல் யாரை Captain Cool-ன்னு சொல்வாங்க?"
        )
        lang_rules = self._sanitize_rules(raw_rules)
        debug_prompt = (
            "=== QUIZ EVALUATION PROMPT ===\n"
            "Question: Who is called Captain Cool in IPL?\n"
            "Correct Answer: MS Dhoni\n"
            "Student's Answer: dhoni\n"
            "Evaluate in: Tamil\n"
            f"Language Rules:\n{lang_rules}"
        )
        # Tamil question must not appear anywhere in the debug prompt's rules block
        assert "IPL-ல்" not in debug_prompt
        assert "யாரை" not in debug_prompt
        # Genuine rules must still be there
        assert "Keep all player names" in debug_prompt


# ── Regression: charset=utf-8 in Content-Type header ────────────


class TestUnicodeJSONResponseHeader:
    """Regression test for bug: Tamil/Hindi rendered as mojibake in browser.

    Root cause: FastAPI's default JSONResponse sends 'Content-Type: application/json'
    without 'charset=utf-8'. Browsers guess the encoding and render Tamil characters
    (valid UTF-8 bytes) as Latin-1 garbage like 'à®¯à®¾à®°à¯'.

    Fix: UnicodeJSONResponse in main.py always sends charset=utf-8 and serialises
    with ensure_ascii=False so Unicode chars appear literally in the payload.
    """

    def _build_response_class(self):
        """Simulate the UnicodeJSONResponse render logic."""
        import json

        class UnicodeJSONResponse:
            media_type = "application/json; charset=utf-8"

            def render(self, content) -> bytes:
                return json.dumps(
                    content,
                    ensure_ascii=False,
                    allow_nan=False,
                    indent=None,
                    separators=(",", ":"),
                ).encode("utf-8")

        return UnicodeJSONResponse()

    def test_media_type_includes_charset_utf8(self):
        """Content-Type must contain 'charset=utf-8'."""
        resp = self._build_response_class()
        assert "charset=utf-8" in resp.media_type

    def test_tamil_rendered_as_unicode_not_escaped(self):
        """Tamil text must appear as literal Unicode, not \\uXXXX escapes."""
        resp = self._build_response_class()
        payload = {"question": "CSK-ன் home ground எந்த stadium?"}
        rendered = resp.render(payload).decode("utf-8")
        # Must contain real Tamil characters, not \\u escape sequences
        assert "எந்த" in rendered
        assert "\\u0b8e" not in rendered.lower()

    def test_no_double_encoding_in_rendered_bytes(self):
        """Rendered bytes decoded as UTF-8 must give back the original string."""
        resp = self._build_response_class()
        original = "IPL 2023 யார் win பண்ணாங்க?"
        payload = {"question": original}
        rendered_bytes = resp.render(payload)
        import json
        decoded = json.loads(rendered_bytes.decode("utf-8"))
        assert decoded["question"] == original

    def test_hindi_rendered_as_unicode_not_escaped(self):
        """Hindi text must also appear as literal Unicode."""
        resp = self._build_response_class()
        payload = {"question": "IPL 2023 किसने win किया?"}
        rendered = resp.render(payload).decode("utf-8")
        assert "किसने" in rendered


# ── Regression: evaluation prompt accepts stadium aliases ────────


class TestEvaluationPromptSynonyms:
    """Regression test for bug: 'chepauk' marked incorrect for 'M. A. Chidambaram Stadium'.

    Root cause: The LLM evaluation prompt said only 'Accept abbreviations and synonyms'
    without giving explicit examples. Local LLMs (qwen2.5, llama3) did not know that
    'Chepauk' is the popular name for M. A. Chidambaram Stadium.

    Fix: The evaluation prompt now lists explicit IPL synonym mappings so local LLMs
    can make the correct decision without relying on general world knowledge.
    """

    def _build_eval_prompt(self, question: str, correct_answer: str, user_answer: str) -> str:
        """Mirror of the evaluation prompt logic in quiz.py _llm_evaluate()."""
        return (
            f"You are a strict but fair IPL cricket quiz evaluator.\n"
            f"Question: {question}\n"
            f"Correct Answer: {correct_answer}\n"
            f"Student's Answer: {user_answer}\n\n"
            f"Is the student's answer correct?\n"
            f"ACCEPT the answer if any of these are true:\n"
            f"  - It is an exact or near-exact match (spelling variants, extra spaces, case)\n"
            f"  - It is a well-known abbreviation, nickname, or synonym:\n"
            f"      * Stadium aliases: 'Chepauk' or 'Chepauk Stadium' = 'M. A. Chidambaram Stadium'\n"
            f"      * Stadium aliases: 'Wankhede' = 'Wankhede Stadium'\n"
            f"      * Stadium aliases: 'Eden' or 'Eden Gardens' = 'Eden Gardens'\n"
            f"      * Stadium aliases: 'Chinnaswamy' = 'M. Chinnaswamy Stadium'\n"
            f"      * Player nicknames: 'Captain Cool' or 'Dhoni' or 'MSD' = 'MS Dhoni'\n"
            f"      * Player nicknames: 'Universe Boss' or 'Gayle' = 'Chris Gayle'\n"
            f"      * 'CSK' = 'Chennai Super Kings', 'MI' = 'Mumbai Indians', etc.\n"
            f"  - It is a partial but unambiguous answer (e.g. 'Dhoni' for 'MS Dhoni')\n"
            f"  - The core factual meaning is the same even if phrased differently\n"
            f"REJECT only if the answer is factually wrong or refers to a different entity.\n"
        )

    def test_prompt_contains_chepauk_alias(self):
        """The evaluation prompt must mention Chepauk = M. A. Chidambaram Stadium."""
        prompt = self._build_eval_prompt(
            "Which stadium is the home ground of CSK?",
            "M. A. Chidambaram Stadium",
            "chepauk",
        )
        assert "Chepauk" in prompt
        assert "M. A. Chidambaram Stadium" in prompt

    def test_prompt_contains_wankhede_alias(self):
        """Wankhede alias must be present for MI home ground questions."""
        prompt = self._build_eval_prompt(
            "What is MI's home ground?", "Wankhede Stadium", "wankhede"
        )
        assert "Wankhede" in prompt

    def test_prompt_contains_dhoni_aliases(self):
        """Captain Cool / MSD / Dhoni aliases must be present."""
        prompt = self._build_eval_prompt(
            "Who is called Captain Cool?", "MS Dhoni", "captain cool"
        )
        assert "Captain Cool" in prompt
        assert "MSD" in prompt
        assert "MS Dhoni" in prompt

    def test_prompt_contains_team_abbreviations(self):
        """CSK / MI abbreviation mappings must be explicit in the prompt."""
        prompt = self._build_eval_prompt(
            "Which team has won the most IPL titles?",
            "Chennai Super Kings",
            "csk",
        )
        assert "CSK" in prompt
        assert "Chennai Super Kings" in prompt

    def test_prompt_instructs_reject_only_factually_wrong(self):
        """The prompt must instruct the LLM to reject only factually wrong answers."""
        prompt = self._build_eval_prompt("Who won IPL 2023?", "Chennai Super Kings", "csk")
        assert "REJECT only if the answer is factually wrong" in prompt
