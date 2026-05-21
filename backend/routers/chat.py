"""
Chat Router — /api/chat (SSE streaming)
"""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from db.mysql import execute, fetch_one, get_db
from models.schemas import ChatRequest
from services.intent_router import detect_intent, get_smalltalk_reply
from services.rag_service import rag_stream
from services.sql_service import sql_stream

logger = logging.getLogger(__name__)
router = APIRouter()


async def _event_generator(body: ChatRequest, db: Session):
    """
    Core SSE generator:
    1. Credit check
    2. Intent detection (smalltalk | sql | quiz | rag)
    3. Stream from appropriate service with heartbeat pings
    4. Deduct credit
    5. Save chat history
    """
    logger.info("Chat — user_id=%s  lang=%s  msg=%r", body.user_id, body.language, body.message[:60])

    # ── 1. Credit check ───────────────────────────────────────
    user = fetch_one(
        db,
        "SELECT id, credits FROM users WHERE id = :uid AND is_active = 1 LIMIT 1",
        {"uid": body.user_id},
    )
    if not user:
        yield f"data: {json.dumps({'token': '⚠️ User not found.'})}\n\n"
        yield "data: [DONE]\n\n"
        return

    if user["credits"] <= 0:
        msg = {
            "en": "⚠️ You have no credits remaining. Please contact support.",
            "ta": "⚠️ உங்கள் credits தீர்ந்துவிட்டன. Support-ஐ தொடர்பு கொள்ளுங்க.",
            "hi": "⚠️ आपके credits खत्म हो गए हैं। Support से संपर्क करें।",
        }.get(body.language, "⚠️ No credits remaining.")
        yield f"data: {json.dumps({'token': msg})}\n\n"
        yield "data: [DONE]\n\n"
        return

    # ── 2. Intent detection ───────────────────────────────────
    intent = detect_intent(body.message)
    logger.info("Intent: %s", intent)

    # ── 3. Smalltalk — instant reply, no LLM, no credit deduction ─
    if intent == "smalltalk":
        reply = get_smalltalk_reply(body.message, body.language)
        yield f"data: {json.dumps({'token': reply})}\n\n"
        yield "data: [DONE]\n\n"
        return

    # ── Check prompt debug flag (admin only) ──────────────────
    debug_flag_row = fetch_one(db, "SELECT show_prompt_debug FROM global_ai_settings WHERE id=1", {})
    show_debug = bool(debug_flag_row["show_prompt_debug"]) if debug_flag_row else False

    full_response = ""
    source_file   = None
    debug_prompt  = None
    queue: asyncio.Queue = asyncio.Queue()

    async def _producer():
        try:
            if intent == "rag":
                async for chunk in rag_stream(body.message, body.language, db=db):
                    await queue.put(chunk)

            elif intent == "sql":
                async for chunk in sql_stream(body.user_id, body.message, body.language, db):
                    await queue.put(chunk)

            elif intent == "quiz":
                msg = {
                    "en": "To start a quiz, type a topic like: 'Quiz me on IPL teams' or 'Quiz me on player records'.",
                    "ta": "Quiz start பண்ண: 'IPL teams பத்தி quiz' அல்லது 'player records quiz' என்று type பண்ணுங்க.",
                    "hi": "Quiz शुरू करने के लिए: 'IPL teams पर quiz' या 'player records पर quiz' लिखें।",
                }.get(body.language, "Type a topic to start a quiz.")
                await queue.put({"token": msg})

        except Exception as exc:
            logger.exception("Service error: %s", exc)
            await queue.put({"token": f"⚠️ Error: {exc}"})
        finally:
            await queue.put(None)

    task = asyncio.create_task(_producer())

    while True:
        try:
            chunk = await asyncio.wait_for(asyncio.shield(queue.get()), timeout=3.0)
        except asyncio.TimeoutError:
            yield ": heartbeat\n\n"
            continue

        if chunk is None:
            break

        if "token" in chunk:
            full_response += chunk["token"]
            yield f"data: {json.dumps({'token': chunk['token']})}\n\n"
        if "source" in chunk:
            source_file = chunk["source"]
            yield f"data: {json.dumps({'source': source_file})}\n\n"
        if "debug_prompt" in chunk:
            debug_prompt = chunk["debug_prompt"]

    await task

    # Emit debug prompt if flag is ON
    if show_debug and debug_prompt:
        yield f"data: {json.dumps({'debug_prompt': debug_prompt})}\n\n"

    # ── 5. Deduct 1 credit ────────────────────────────────────
    new_credits = max(0, user["credits"] - 1)
    execute(db, "UPDATE users SET credits = :c WHERE id = :uid", {"c": new_credits, "uid": body.user_id})
    try:
        execute(
            db,
            "INSERT INTO credit_transactions (user_id, delta, reason, balance) VALUES (:uid,-1,'chat_message',:b)",
            {"uid": body.user_id, "b": new_credits},
        )
    except Exception:
        pass
    yield f"data: {json.dumps({'credits': new_credits})}\n\n"

    # ── 6. Save chat history ──────────────────────────────────
    try:
        execute(db,
            "INSERT INTO chat_history (user_id, role, message, intent, language) VALUES (:uid,'user',:msg,:intent,:lang)",
            {"uid": body.user_id, "msg": body.message, "intent": intent, "lang": body.language},
        )
        execute(db,
            "INSERT INTO chat_history (user_id, role, message, intent, source_file, language) VALUES (:uid,'assistant',:msg,:intent,:src,:lang)",
            {"uid": body.user_id, "msg": full_response, "intent": intent, "src": source_file, "lang": body.language},
        )
    except Exception as exc:
        logger.warning("Chat history save failed: %s", exc)

    logger.info("Chat done — intent=%s  credits_left=%d", intent, new_credits)
    yield "data: [DONE]\n\n"


@router.post("/chat")
async def chat(body: ChatRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    return StreamingResponse(
        _event_generator(body, db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
