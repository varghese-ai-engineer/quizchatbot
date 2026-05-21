"""
QuizChatbot FastAPI Application Entry Point
"""
import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routers import auth, chat, quiz, admin


class UnicodeJSONResponse(JSONResponse):
    r"""
    FastAPI's default JSONResponse omits 'charset=utf-8' from the
    Content-Type header.  Some browsers then guess the encoding and
    mis-render Tamil/Hindi Unicode as Latin-1 mojibake.

    This subclass forces 'Content-Type: application/json; charset=utf-8'
    on every response, and serialises with ensure_ascii=False so the
    JSON payload itself contains real Unicode characters (smaller payload,
    easier debugging) rather than \uXXXX escape sequences.
    """
    media_type = "application/json; charset=utf-8"

    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")


app = FastAPI(
    title="QuizChatbot API",
    version="1.0.0",
    description="Multilingual AI-Powered Training Assistant API",
    default_response_class=UnicodeJSONResponse,
)

# ── CORS ─────────────────────────────────────────────────────
# NOTE: allow_credentials=True + allow_origins=["*"] is INVALID per CORS spec.
# Browsers silently drop the Access-Control-Allow-Origin header in that combo.
# Auth uses JWT in headers (not cookies), so credentials=False is correct here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8090",   # PHP frontend (local)
        "http://localhost:8100",   # API self
        "http://localhost",
        "http://127.0.0.1:8090",
        "http://127.0.0.1",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────
app.include_router(auth.router,  prefix="/api/auth",  tags=["Auth"])
app.include_router(chat.router,  prefix="/api",       tags=["Chat"])
app.include_router(quiz.router,  prefix="/api/quiz",  tags=["Quiz"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])


import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    return {"status": "ok", "service": "QuizChatbot API"}


@app.get("/api/test-ollama", tags=["Health"])
async def test_ollama() -> dict:
    """Quick smoke-test: embedding + one LLM token. Open in browser to debug."""
    import httpx
    from config import settings

    result: dict = {}

    # Test 1 — embedding
    try:
        r = await httpx.AsyncClient(timeout=30).post(
            f"{settings.ollama_host}/api/embeddings",
            json={"model": settings.embed_model, "prompt": "test"},
        )
        emb = r.json().get("embedding", [])
        result["embedding"] = f"✅ {len(emb)}-dim vector"
    except Exception as e:
        result["embedding"] = f"❌ {e}"

    # Test 2 — LLM (single token)
    try:
        r = await httpx.AsyncClient(timeout=60).post(
            f"{settings.ollama_host}/api/chat",
            json={
                "model": settings.llm_model,
                "messages": [{"role": "user", "content": "Say only the word OK"}],
                "stream": False,
            },
        )
        reply = r.json().get("message", {}).get("content", "")
        result["llm"] = f"✅ Response: {reply[:80]!r}"
    except Exception as e:
        result["llm"] = f"❌ {e}"

    return result
