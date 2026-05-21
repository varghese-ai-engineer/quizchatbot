"""
Admin Router — API endpoints for the admin panel.
All endpoints require X-Admin-Key header matching settings.admin_key.
"""
from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import traceback
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from db.mysql import execute, fetch_all, fetch_one, get_db

logger = logging.getLogger(__name__)
router = APIRouter()

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge_base"


def _require_admin(x_admin_key: str = Header(default="")):
    if x_admin_key != getattr(settings, "admin_key", "admin123"):
        raise HTTPException(status_code=403, detail="Forbidden")


# ── Knowledge Files ───────────────────────────────────────────

@router.get("/knowledge/list")
def list_knowledge_files(db: Session = Depends(get_db), _=Depends(_require_admin)):
    rows = fetch_all(db, """
        SELECT id, filename, domain_name, topics_json, keywords_json,
               ai_language_rules, chunk_count, indexed_at, status
        FROM knowledge_files ORDER BY indexed_at DESC
    """, {})
    return rows or []


@router.post("/knowledge/upload")
async def upload_knowledge_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _=Depends(_require_admin),
):
    if not file.filename.endswith(".md"):
        raise HTTPException(400, "Only .md files are supported")

    dest = KNOWLEDGE_DIR / file.filename
    content = await file.read()
    dest.write_bytes(content)

    # 1. Run ChromaDB ingest in background subprocess
    try:
        subprocess.Popen([
            "python", "scripts/ingest_knowledge_base.py",
            "--file", file.filename,
        ], cwd=str(KNOWLEDGE_DIR.parent))
    except Exception as e:
        logger.warning("Could not start ingest subprocess: %s", e)

    # 2. Auto-generate quiz questions from the uploaded file (background task)
    async def _generate_quiz_bg():
        try:
            from services.quiz_generator import generate_and_store_questions
            from db.mysql import SessionLocal, fetch_one as db_fetch_one
            bg_db = SessionLocal()
            try:
                # Wait up to 30 s for the ingest script to register the file in MySQL
                import asyncio
                kf_id = None
                for _ in range(6):
                    row = db_fetch_one(
                        bg_db,
                        "SELECT id FROM knowledge_files WHERE filename = :fn",
                        {"fn": file.filename},
                    )
                    if row:
                        kf_id = row["id"]
                        break
                    await asyncio.sleep(5)

                result = await generate_and_store_questions(dest, bg_db, knowledge_file_id=kf_id)
                logger.info(
                    "Quiz auto-generation result for %s: %s (knowledge_file_id=%s)",
                    file.filename, result, kf_id
                )
            finally:
                bg_db.close()
        except Exception as e:
            logger.error(
                "Quiz auto-generation failed for %s: %r\n%s",
                file.filename, e, traceback.format_exc()
            )

    asyncio.create_task(_generate_quiz_bg())

    return {
        "status": "ok",
        "message": f"{file.filename} uploaded. Indexing and quiz generation started in background.",
    }


@router.delete("/knowledge/{filename}")
def delete_knowledge_file(
    filename: str,
    db: Session = Depends(get_db),
    _=Depends(_require_admin),
):
    # ── Step 1: Physical file ────────────────────────────────
    dest = KNOWLEDGE_DIR / filename
    if dest.exists():
        dest.unlink()
        logger.info("Deleted physical file: %s", filename)

    # ── Step 2: ChromaDB vectors ─────────────────────────────
    try:
        from db.chroma import get_collection
        collection = get_collection()
        old = collection.get(where={"source": filename})
        if old["ids"]:
            collection.delete(ids=old["ids"])
            logger.info("Deleted %d ChromaDB chunks for %s", len(old["ids"]), filename)
    except Exception as e:
        logger.warning("ChromaDB delete error for %s: %s", filename, e)

    # ── Step 3: MySQL knowledge_files row ────────────────────
    # CASCADE from knowledge_files automatically removes:
    #   answer_aliases (ON DELETE CASCADE)
    #   quiz_topics    (ON DELETE CASCADE) → quiz_questions → quiz_answers
    kf_row = fetch_one(db, "SELECT id FROM knowledge_files WHERE filename = :fn", {"fn": filename})
    if kf_row:
        kf_id = kf_row["id"]
        # Verify cascade coverage — log what will be removed
        topic_count = fetch_one(db,
            "SELECT COUNT(*) AS cnt FROM quiz_topics WHERE knowledge_file_id = :id",
            {"id": kf_id}
        )
        alias_count = fetch_one(db,
            "SELECT COUNT(*) AS cnt FROM answer_aliases WHERE knowledge_file_id = :id",
            {"id": kf_id}
        )
        logger.info(
            "Deleting knowledge_file id=%s ('%s'): will cascade-delete %s topic(s), %s alias(es)",
            kf_id, filename,
            topic_count["cnt"] if topic_count else 0,
            alias_count["cnt"] if alias_count else 0,
        )
        execute(db, "DELETE FROM knowledge_files WHERE id = :id", {"id": kf_id})
    else:
        # File wasn't in MySQL — still attempt cleanup by filename
        execute(db, "DELETE FROM knowledge_files WHERE filename = :fn", {"fn": filename})
        logger.warning("knowledge_files row not found for '%s' — deleted by filename anyway", filename)

    logger.info("Delete complete for '%s'", filename)
    return {"status": "ok", "message": f"{filename} and all related data deleted."}


@router.post("/knowledge/reindex/{filename}")
def reindex_knowledge_file(
    filename: str,
    db: Session = Depends(get_db),
    _=Depends(_require_admin),
):
    execute(db, "UPDATE knowledge_files SET status='pending' WHERE filename=:fn", {"fn": filename})
    try:
        subprocess.Popen([
            "python", "scripts/ingest_knowledge_base.py",
            "--file", filename,
        ], cwd=str(KNOWLEDGE_DIR.parent))
    except Exception as e:
        raise HTTPException(500, f"Could not start reindex: {e}")
    return {"status": "ok", "message": f"Re-indexing {filename} started."}


@router.post("/knowledge/retranslate/{topic_id}")
async def retranslate_topic_questions(
    topic_id: int,
    db: Session = Depends(get_db),
    _=Depends(_require_admin),
):
    """
    Re-translate all questions for a topic using the latest improved prompts.
    Fixes existing bad Tamil/Hindi translations without requiring file re-upload.
    Runs in background — returns immediately.
    """
    topic = fetch_one(db, "SELECT id, name FROM quiz_topics WHERE id = :id", {"id": topic_id})
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found.")

    async def _retranslate_bg():
        try:
            from services.quiz_generator import translate_questions
            from db.mysql import SessionLocal, fetch_all as db_fetch_all, execute as db_execute
            import json
            bg_db = SessionLocal()
            try:
                rows = db_fetch_all(bg_db, """
                    SELECT id, question, answer, options, type
                    FROM quiz_questions WHERE topic_id = :tid AND is_active = 1
                """, {"tid": topic_id})

                if not rows:
                    logger.info("Retranslate — no questions found for topic_id=%s", topic_id)
                    return

                # Build list compatible with translate_questions()
                questions = []
                for i, r in enumerate(rows):
                    questions.append({
                        "idx":      i,
                        "question": r["question"],
                        "answer":   r["answer"],
                        "type":     r["type"],
                        "options":  json.loads(r["options"]) if r["options"] else None,
                    })

                # Re-translate Tamil
                q_ta = await translate_questions(questions, "ta")
                # Re-translate Hindi
                q_hi = await translate_questions(q_ta, "hi")

                # Build lookup by idx
                ta_map = {q["idx"]: q for q in q_ta}
                hi_map = {q["idx"]: q for q in q_hi}

                updated = 0
                for i, r in enumerate(rows):
                    ta = ta_map.get(i, {})
                    hi = hi_map.get(i, {})
                    opts_ta = json.dumps(ta.get("options_ta"), ensure_ascii=False) if ta.get("options_ta") else None
                    opts_hi = json.dumps(hi.get("options_hi"), ensure_ascii=False) if hi.get("options_hi") else None
                    db_execute(bg_db, """
                        UPDATE quiz_questions
                        SET question_ta = :q_ta, answer_ta = :a_ta, options_ta = :o_ta,
                            question_hi = :q_hi, answer_hi = :a_hi, options_hi = :o_hi
                        WHERE id = :qid
                    """, {
                        "q_ta": ta.get("question_ta", r["question"]),
                        "a_ta": ta.get("answer_ta",   r["answer"]),
                        "o_ta": opts_ta,
                        "q_hi": hi.get("question_hi", r["question"]),
                        "a_hi": hi.get("answer_hi",   r["answer"]),
                        "o_hi": opts_hi,
                        "qid":  r["id"],
                    })
                    updated += 1

                logger.info("Retranslate ✅ %d questions updated for topic_id=%s", updated, topic_id)
            finally:
                bg_db.close()
        except Exception as e:
            logger.error("Retranslate failed for topic_id=%s: %r", topic_id, e)

    import asyncio
    asyncio.create_task(_retranslate_bg())
    return {
        "status": "ok",
        "message": f"Re-translation started for topic '{topic['name']}' ({topic_id}). "
                   f"Questions will update in background (check logs).",
        "topic_id": topic_id,
    }


class UpdateRulesRequest(BaseModel):
    filename: str
    ai_language_rules: str


@router.put("/knowledge/rules")
def update_ai_rules(body: UpdateRulesRequest, db: Session = Depends(get_db), _=Depends(_require_admin)):
    execute(db,
        "UPDATE knowledge_files SET ai_language_rules=:rules WHERE filename=:fn",
        {"rules": body.ai_language_rules, "fn": body.filename},
    )
    return {"status": "ok"}


# ── Global AI Settings ────────────────────────────────────────

@router.get("/settings/global")
def get_global_settings(db: Session = Depends(get_db), _=Depends(_require_admin)):
    row = fetch_one(db, "SELECT * FROM global_ai_settings WHERE id=1", {})
    return row or {}


class UpdateGlobalSettingsRequest(BaseModel):
    global_special_instruction: str


@router.put("/settings/global")
def update_global_settings(
    body: UpdateGlobalSettingsRequest,
    db: Session = Depends(get_db),
    _=Depends(_require_admin),
):
    execute(db,
        """INSERT INTO global_ai_settings (id, global_special_instruction)
           VALUES (1, :inst)
           ON DUPLICATE KEY UPDATE global_special_instruction=VALUES(global_special_instruction)""",
        {"inst": body.global_special_instruction},
    )
    return {"status": "ok"}


# ── Quiz Config ───────────────────────────────────────────────

@router.get("/quiz-config")
def get_quiz_config(db: Session = Depends(get_db), _=Depends(_require_admin)):
    row = fetch_one(db, "SELECT * FROM quiz_config WHERE id = 1", {})
    return row or {}


class UpdateQuizConfigRequest(BaseModel):
    num_questions: int
    marks_per_q: int
    pass_mark_pct: int
    question_type: str  # mcq | open | both
    intro_text: str = ""


@router.put("/quiz-config")
def update_quiz_config(body: UpdateQuizConfigRequest, db: Session = Depends(get_db), _=Depends(_require_admin)):
    if body.question_type not in ("mcq", "open", "both"):
        raise HTTPException(status_code=400, detail="question_type must be mcq, open, or both")
    if not (1 <= body.num_questions <= 100):
        raise HTTPException(status_code=400, detail="num_questions must be 1–100")
    if not (1 <= body.marks_per_q <= 100):
        raise HTTPException(status_code=400, detail="marks_per_q must be 1–100")
    if not (1 <= body.pass_mark_pct <= 100):
        raise HTTPException(status_code=400, detail="pass_mark_pct must be 1–100")

    execute(db,
        """INSERT INTO quiz_config (id, num_questions, marks_per_q, pass_mark_pct, question_type, intro_text)
           VALUES (1, :nq, :mpq, :pmp, :qt, :it)
           ON DUPLICATE KEY UPDATE
               num_questions=VALUES(num_questions),
               marks_per_q=VALUES(marks_per_q),
               pass_mark_pct=VALUES(pass_mark_pct),
               question_type=VALUES(question_type),
               intro_text=VALUES(intro_text)""",
        {"nq": body.num_questions, "mpq": body.marks_per_q,
         "pmp": body.pass_mark_pct, "qt": body.question_type, "it": body.intro_text},
    )
    return {"status": "ok"}


# ── User Management ───────────────────────────────────────────

@router.get("/users/list")
def list_users(
    page: int = 1,
    per_page: int = 20,
    search: str = "",
    db: Session = Depends(get_db),
    _=Depends(_require_admin),
):
    offset = (page - 1) * per_page
    like   = f"%{search}%"
    rows   = fetch_all(db, """
        SELECT u.id, u.username, u.email, u.full_name,
               u.total_credits,
               (u.total_credits - u.credits) AS used_credits,
               u.credits AS balance_credits,
               u.language, u.is_active, u.role,
               u.created_at,
               (SELECT MAX(qs.score) FROM quiz_sessions qs
                WHERE qs.user_id = u.id AND qs.completed=1) AS best_quiz_score
        FROM users u
        WHERE u.username LIKE :s OR u.email LIKE :s OR u.full_name LIKE :s
        ORDER BY u.created_at DESC
        LIMIT :lim OFFSET :off
    """, {"s": like, "lim": per_page, "off": offset})
    return rows or []


class UpdateCreditsRequest(BaseModel):
    user_id: int
    credits: int


@router.put("/users/credits")
def update_user_credits(body: UpdateCreditsRequest, db: Session = Depends(get_db), _=Depends(_require_admin)):
    execute(db,
        "UPDATE users SET credits=:c, total_credits=total_credits+GREATEST(:c - credits, 0) WHERE id=:uid",
        {"c": body.credits, "uid": body.user_id},
    )
    return {"status": "ok"}


class ToggleUserRequest(BaseModel):
    user_id: int
    is_active: int   # 0 or 1


@router.put("/users/toggle")
def toggle_user(body: ToggleUserRequest, db: Session = Depends(get_db), _=Depends(_require_admin)):
    execute(db, "UPDATE users SET is_active=:a WHERE id=:uid",
            {"a": body.is_active, "uid": body.user_id})
    return {"status": "ok"}


@router.get("/users/{user_id}/chat-history")
def get_user_chat_history(user_id: int, db: Session = Depends(get_db), _=Depends(_require_admin)):
    rows = fetch_all(db, """
        SELECT role, message, intent, language, created_at
        FROM chat_history WHERE user_id=:uid ORDER BY created_at DESC LIMIT 50
    """, {"uid": user_id})
    return rows or []


# ── Create User (by Admin) ────────────────────────────────────

class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    role: str = "user"
    credits: int = 100


@router.post("/users/create")
def admin_create_user(body: CreateUserRequest, db: Session = Depends(get_db), _=Depends(_require_admin)):
    import bcrypt

    # Check for duplicate email or username
    existing = fetch_one(db,
        "SELECT id FROM users WHERE email=:email OR username=:username LIMIT 1",
        {"email": body.email, "username": body.username},
    )
    if existing:
        raise HTTPException(status_code=409, detail="Email or username already exists.")

    role = body.role if body.role in ("user", "admin") else "user"
    hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()

    execute(db,
        """INSERT INTO users (username, email, password, full_name, role, credits, total_credits, is_active)
           VALUES (:un, :em, :pw, :fn, :role, :cr, :cr, 1)""",
        {"un": body.username, "em": body.email, "pw": hashed,
         "fn": body.full_name, "role": role, "cr": body.credits},
    )
    return {"status": "ok", "message": f"User '{body.username}' created successfully."}


# ── Reset Credits for All Users ───────────────────────────────

class ResetCreditsRequest(BaseModel):
    credits: int = 100


@router.post("/users/reset-credits")
def reset_all_credits(body: ResetCreditsRequest, db: Session = Depends(get_db), _=Depends(_require_admin)):
    if body.credits < 0:
        raise HTTPException(status_code=400, detail="Credits must be >= 0")
    execute(db,
        "UPDATE users SET credits=:cr, total_credits=:cr WHERE role='user'",
        {"cr": body.credits},
    )
    return {"status": "ok", "message": f"All user credits reset to {body.credits}."}


# ── Update User ───────────────────────────────────────────────

class UpdateUserRequest(BaseModel):
    user_id: int
    full_name: str
    username: str
    email: str
    password: str | None = None


@router.put("/users/update")
def update_user(body: UpdateUserRequest, db: Session = Depends(get_db), _=Depends(_require_admin)):
    import bcrypt

    # Check duplicate email/username on OTHER users
    existing = fetch_one(db,
        "SELECT id FROM users WHERE (email=:email OR username=:username) AND id != :uid LIMIT 1",
        {"email": body.email, "username": body.username, "uid": body.user_id},
    )
    if existing:
        raise HTTPException(status_code=409, detail="Email or username already used by another user.")

    role = body.role if body.role in ("user", "admin") else "user"

    if body.password:
        hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
        execute(db,
            "UPDATE users SET full_name=:fn, username=:un, email=:em, password=:pw WHERE id=:uid",
            {"fn": body.full_name, "un": body.username, "em": body.email,
             "pw": hashed, "uid": body.user_id},
        )
    else:
        execute(db,
            "UPDATE users SET full_name=:fn, username=:un, email=:em WHERE id=:uid",
            {"fn": body.full_name, "un": body.username, "em": body.email,
             "uid": body.user_id},
        )
    return {"status": "ok", "message": "User updated successfully."}


# ── Delete User ───────────────────────────────────────────────

@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), _=Depends(_require_admin)):
    user = fetch_one(db, "SELECT id, role FROM users WHERE id=:uid", {"uid": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user["role"] == "admin":
        raise HTTPException(status_code=403, detail="Cannot delete an admin account.")
    execute(db, "DELETE FROM users WHERE id=:uid", {"uid": user_id})
    return {"status": "ok", "message": "User deleted successfully."}


# ── Prompt Debug Toggle ───────────────────────────────────────

@router.get("/prompt-debug")
def get_prompt_debug(db: Session = Depends(get_db), _=Depends(_require_admin)):
    """Return current show_prompt_debug flag."""
    row = fetch_one(db, "SELECT show_prompt_debug FROM global_ai_settings WHERE id = 1", {})
    return {"show_prompt_debug": bool(row["show_prompt_debug"]) if row else False}


@router.post("/prompt-debug")
def set_prompt_debug(db: Session = Depends(get_db), _=Depends(_require_admin)):
    """Toggle show_prompt_debug flag and return new value."""
    row = fetch_one(db, "SELECT show_prompt_debug FROM global_ai_settings WHERE id = 1", {})
    current = row["show_prompt_debug"] if row else 0
    new_val  = 0 if current else 1
    execute(db,
        "UPDATE global_ai_settings SET show_prompt_debug = :v WHERE id = 1",
        {"v": new_val},
    )
    return {"show_prompt_debug": bool(new_val)}


# ── Answer Aliases ─────────────────────────────────────────────


class AliasCreateBody(BaseModel):
    knowledge_file_id: int
    canonical: str           # "Chennai Super Kings"
    alias: str               # "CSK"


@router.get("/aliases")
def list_aliases(db: Session = Depends(get_db), _=Depends(_require_admin)):
    """Return all answer aliases, grouped with their knowledge file name."""
    rows = fetch_all(db, """
        SELECT aa.id, aa.canonical, aa.alias, aa.created_at,
               kf.filename AS knowledge_file
        FROM answer_aliases aa
        JOIN knowledge_files kf ON aa.knowledge_file_id = kf.id
        ORDER BY kf.filename, aa.canonical, aa.alias
    """, {})
    return rows or []


@router.post("/aliases")
def add_alias(body: AliasCreateBody, db: Session = Depends(get_db), _=Depends(_require_admin)):
    """
    Add a canonical → alias mapping for a knowledge file.
    When the knowledge file is deleted, this alias is auto-deleted (CASCADE).
    """
    # Verify knowledge file exists
    kf = fetch_one(db, "SELECT id FROM knowledge_files WHERE id = :id", {"id": body.knowledge_file_id})
    if not kf:
        raise HTTPException(status_code=404, detail="Knowledge file not found.")

    # Prevent duplicate
    existing = fetch_one(db,
        "SELECT id FROM answer_aliases WHERE knowledge_file_id = :fid AND canonical = :c AND alias = :a",
        {"fid": body.knowledge_file_id, "c": body.canonical.strip(), "a": body.alias.strip()},
    )
    if existing:
        raise HTTPException(status_code=409, detail="Alias already exists.")

    execute(db,
        "INSERT INTO answer_aliases (knowledge_file_id, canonical, alias) VALUES (:fid, :c, :a)",
        {"fid": body.knowledge_file_id, "c": body.canonical.strip(), "a": body.alias.strip()},
    )
    return {"status": "created", "canonical": body.canonical, "alias": body.alias}


@router.delete("/aliases/{alias_id}")
def delete_alias(alias_id: int, db: Session = Depends(get_db), _=Depends(_require_admin)):
    """Remove a single alias entry."""
    row = fetch_one(db, "SELECT id FROM answer_aliases WHERE id = :id", {"id": alias_id})
    if not row:
        raise HTTPException(status_code=404, detail="Alias not found.")
    execute(db, "DELETE FROM answer_aliases WHERE id = :id", {"id": alias_id})
    return {"status": "deleted", "id": alias_id}


@router.get("/aliases/by-canonical")
def get_aliases_for_canonical(
    canonical: str,
    db: Session = Depends(get_db),
    _=Depends(_require_admin),
):
    """Fetch all aliases for a specific canonical answer string (for live preview)."""
    rows = fetch_all(db,
        "SELECT id, alias, created_at FROM answer_aliases WHERE canonical = :c",
        {"c": canonical},
    )
    return {"canonical": canonical, "aliases": rows or []}
