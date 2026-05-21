"""
Regression Tests — SSE Event Format (chat.py)
Verifies the typed SSE frame helpers produce correct output format.
Run: pytest backend/tests/test_sse_format.py -v
"""
import json
import sys
import os
import types

# ── Stub heavy dependencies so we can import the three pure helpers ──
# _token_event / _meta_event / _done_event have no external imports;
# we only need to prevent the module-level router/fastapi imports from failing.
for _name in [
    "fastapi", "fastapi.responses", "sqlalchemy", "sqlalchemy.orm",
    "db", "db.mysql", "models", "models.schemas",
    "services", "services.intent_router",
    "services.rag_service", "services.sql_service", "config",
]:
    if _name not in sys.modules:
        sys.modules[_name] = types.ModuleType(_name)

# Minimal attribute stubs required at import time
sys.modules["fastapi"].APIRouter   = type("APIRouter", (), {"post": lambda *a, **kw: (lambda f: f)})
sys.modules["fastapi"].Depends     = lambda f: f
_fr = types.ModuleType("fastapi.responses")
_fr.StreamingResponse              = object
sys.modules["fastapi.responses"]   = _fr
sys.modules["sqlalchemy.orm"].Session = object
sys.modules["db.mysql"].execute    = lambda *a, **kw: None
sys.modules["db.mysql"].fetch_one  = lambda *a, **kw: {}
sys.modules["db.mysql"].get_db     = lambda: None
sys.modules["models.schemas"].ChatRequest = object
sys.modules["services.intent_router"].detect_intent    = lambda m: "rag"
sys.modules["services.intent_router"].get_smalltalk_reply = lambda m, l: ""
sys.modules["services.rag_service"].rag_stream         = None
sys.modules["services.sql_service"].sql_stream         = None

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from routers.chat import _token_event, _meta_event, _done_event   # noqa: E402


# ─── SSE Frame Format Tests ───────────────────────────────────

class TestTokenEvent:
    """_token_event must produce a correctly typed SSE token frame."""

    def test_has_event_type(self):
        frame = _token_event("hello")
        assert "event: token" in frame

    def test_has_data_field(self):
        frame = _token_event("hello")
        assert "data: " in frame

    def test_data_is_valid_json(self):
        frame = _token_event("hello world")
        data_line = [l for l in frame.split("\n") if l.startswith("data:")][0]
        parsed = json.loads(data_line[5:].strip())
        assert parsed["token"] == "hello world"

    def test_ends_with_double_newline(self):
        frame = _token_event("x")
        assert frame.endswith("\n\n")

    def test_event_before_data(self):
        """SSE spec: 'event:' must appear before 'data:' in the frame."""
        frame = _token_event("test")
        lines = [l for l in frame.split("\n") if l.strip()]
        event_idx = next(i for i, l in enumerate(lines) if l.startswith("event:"))
        data_idx  = next(i for i, l in enumerate(lines) if l.startswith("data:"))
        assert event_idx < data_idx

    def test_unicode_token(self):
        """Tamil and Hindi tokens must be preserved through JSON encoding."""
        frame = _token_event("சிறந்த கேள்வி!")
        data_line = [l for l in frame.split("\n") if l.startswith("data:")][0]
        parsed = json.loads(data_line[5:].strip())
        assert parsed["token"] == "சிறந்த கேள்வி!"

    def test_special_chars_in_token(self):
        """Quotes and backslashes must be JSON-escaped."""
        frame = _token_event('He said "hello"')
        data_line = [l for l in frame.split("\n") if l.startswith("data:")][0]
        parsed = json.loads(data_line[5:].strip())
        assert parsed["token"] == 'He said "hello"'

    def test_empty_token(self):
        """Empty string token still produces a valid frame."""
        frame = _token_event("")
        data_line = [l for l in frame.split("\n") if l.startswith("data:")][0]
        parsed = json.loads(data_line[5:].strip())
        assert parsed["token"] == ""


class TestMetaEvent:
    """_meta_event must produce a correctly typed SSE meta frame."""

    def test_has_event_type(self):
        frame = _meta_event({"credits": 42})
        assert "event: meta" in frame

    def test_credits_payload(self):
        frame = _meta_event({"credits": 42})
        data_line = [l for l in frame.split("\n") if l.startswith("data:")][0]
        parsed = json.loads(data_line[5:].strip())
        assert parsed["credits"] == 42

    def test_source_payload(self):
        frame = _meta_event({"source": "players.md"})
        data_line = [l for l in frame.split("\n") if l.startswith("data:")][0]
        parsed = json.loads(data_line[5:].strip())
        assert parsed["source"] == "players.md"

    def test_combined_meta_payload(self):
        frame = _meta_event({"source": "teams.md", "credits": 10})
        data_line = [l for l in frame.split("\n") if l.startswith("data:")][0]
        parsed = json.loads(data_line[5:].strip())
        assert parsed["source"] == "teams.md"
        assert parsed["credits"] == 10

    def test_ends_with_double_newline(self):
        frame = _meta_event({"credits": 1})
        assert frame.endswith("\n\n")

    def test_data_is_valid_json(self):
        frame = _meta_event({"credits": 5, "source": "a.md"})
        data_line = [l for l in frame.split("\n") if l.startswith("data:")][0]
        json.loads(data_line[5:].strip())   # must not raise


class TestDoneEvent:
    """_done_event must produce a terminal SSE frame."""

    def test_has_done_event_type(self):
        frame = _done_event()
        assert "event: done" in frame

    def test_data_is_done_sentinel(self):
        frame = _done_event()
        assert "data: [DONE]" in frame

    def test_ends_with_double_newline(self):
        frame = _done_event()
        assert frame.endswith("\n\n")

    def test_done_is_literal_not_json(self):
        """[DONE] must be the literal string, not JSON-encoded."""
        frame = _done_event()
        data_line = [l for l in frame.split("\n") if l.startswith("data:")][0]
        raw = data_line[5:].strip()
        assert raw == "[DONE]"


class TestSSEFrameSeparation:
    """Each event must be separated from the next by a blank line (\\n\\n)."""

    def test_token_frame_has_two_trailing_newlines(self):
        frame = _token_event("hi")
        assert frame.endswith("\n\n")

    def test_meta_frame_has_two_trailing_newlines(self):
        frame = _meta_event({"credits": 3})
        assert frame.endswith("\n\n")

    def test_done_frame_has_two_trailing_newlines(self):
        frame = _done_event()
        assert frame.endswith("\n\n")

    def test_consecutive_frames_have_blank_line_between_them(self):
        combined = _token_event("a") + _meta_event({"credits": 9}) + _done_event()
        # At minimum 3 double-newline separators
        assert combined.count("\n\n") >= 3
