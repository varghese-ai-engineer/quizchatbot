"""
Quiz Generator Service
Automatically generates quiz questions from a knowledge base .md file
and stores them in MySQL with Tamil + Hindi translations.

Called after a new .md file is uploaded via the admin panel.
"""
from __future__ import annotations

import json
import logging
import re
import traceback
from pathlib import Path
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from config import settings
from db.mysql import execute, fetch_one

logger = logging.getLogger(__name__)

LANG_NAMES = {"ta": "Tamil", "hi": "Hindi"}

# ── Prompt Templates ──────────────────────────────────────────

_GENERATE_PROMPT = """\
You are a quiz question generator. Read the following knowledge base content and generate quiz questions.

Generate exactly:
- 3 open-ended questions (type: "open")
- 5 multiple choice questions (type: "mcq") with exactly 4 options each

Rules:
- Questions must be directly answerable from the content below
- Keep player names, team names, and numbers in English
- Vary difficulty: mix easy, medium, hard
- For MCQ: include the correct answer as one of the 4 options
- Return ONLY a valid JSON array — no explanation, no markdown

JSON format for each question:
{{
  "question": "...",
  "type": "open" or "mcq",
  "answer": "...",
  "options": null (for open) or ["opt1","opt2","opt3","opt4"] (for mcq),
  "difficulty": "easy" or "medium" or "hard"
}}

Knowledge base content:
---
{content}
---

Return the JSON array:"""


_TRANSLATE_PROMPT_TA = """\
Translate these quiz questions from English to SIMPLE, SPOKEN Tamil mixed with English words.

STRICT RULES:
1. Keep ALL player names in ENGLISH: Chris Gayle, MS Dhoni (NEVER transliterate)
2. Keep ALL team names in ENGLISH: CSK, MI, RCB, KKR (NEVER write in Tamil script)
3. Keep ALL numbers in ENGLISH: 175*, 358, 2013
4. Use simple spoken Tamil for question and answer text
5. Do NOT transliterate English words into Tamil script
6. Return ONLY valid JSON — no explanation

CORRECT example:
  English: "Who scored the most runs in IPL history?"
  Tamil:   "IPL history-ல் அதிக runs யார் அடிச்சாங்க?"

Translate ONLY question, answer, options fields. Keep id, type, difficulty exactly the same.

Questions JSON:
{questions_json}

Return translated JSON array:"""


_TRANSLATE_PROMPT_HI = """\
Translate these quiz questions from English to SIMPLE, SPOKEN Hindi mixed with English words.

STRICT RULES:
1. Keep ALL player names in ENGLISH: Chris Gayle, MS Dhoni (NEVER transliterate)
2. Keep ALL team names in ENGLISH: CSK, MI, RCB, KKR (NEVER write in Hindi script)
3. Keep ALL numbers in ENGLISH: 175*, 358, 2013
4. Use simple spoken Hindi for question and answer text
5. Do NOT transliterate English words into Hindi script
6. Return ONLY valid JSON — no explanation

CORRECT example:
  English: "Who scored the most runs in IPL history?"
  Hindi:   "IPL history में सबसे ज्यादा runs किसने बनाए?"

Translate ONLY question, answer, options fields. Keep id, type, difficulty exactly the same.

Questions JSON:
{questions_json}

Return translated JSON array:"""


# ── LLM Helpers ───────────────────────────────────────────────

async def _call_llm(prompt: str, timeout: int = 120) -> str:
    """Call Ollama and return the raw response text."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(
            f"{settings.ollama_host}/api/generate",
            json={"model": settings.llm_model, "prompt": prompt, "stream": False},
        )
        r.raise_for_status()
        return r.json().get("response", "").strip()


def _extract_json_array(raw: str) -> list:
    """Extract the first JSON array found in a string.

    Handles:
    - Bare arrays:  [{ ... }]
    - Markdown code fences: ```json\n[...]\n```
    - Wrapped objects:  { "questions": [...] }  (LLM sometimes wraps output)
    """
    # Strip markdown code fences if present
    raw = re.sub(r"```(?:json)?", "", raw).strip()

    # 1. Try to find a bare JSON array first
    start = raw.find("[")
    end   = raw.rfind("]") + 1
    if start != -1 and end > 0:
        try:
            return json.loads(raw[start:end])
        except json.JSONDecodeError:
            pass  # fall through to wrapped-object attempt

    # 2. Try parsing the whole response as a JSON object and look for a list value
    try:
        obj = json.loads(raw)
        if isinstance(obj, list):
            return obj
        if isinstance(obj, dict):
            # Return the first value that is a list
            for v in obj.values():
                if isinstance(v, list):
                    return v
    except json.JSONDecodeError:
        pass

    return []


# ── Core Functions ────────────────────────────────────────────

async def generate_questions_from_content(content: str) -> list[dict]:
    """Call LLM to generate quiz questions from markdown content."""
    # Truncate very long files to avoid token limits
    truncated = content[:6000] if len(content) > 6000 else content
    prompt = _GENERATE_PROMPT.format(content=truncated)

    try:
        raw = await _call_llm(prompt, timeout=120)
        questions = _extract_json_array(raw)
        if not isinstance(questions, list):
            logger.error("Quiz generator — LLM returned non-list type: %s", type(questions))
            return []
        # Validate and normalise
        valid = []
        for i, q in enumerate(questions):
            if not isinstance(q, dict):
                logger.warning("Quiz generator — skipping non-dict item at index %d: %r", i, q)
                continue
            if not q.get("question") or not q.get("answer"):
                continue
            valid.append({
                "idx":        i,
                "question":   str(q["question"]).strip(),
                "type":       q.get("type", "open") if q.get("type") in ("open", "mcq") else "open",
                "answer":     str(q["answer"]).strip(),
                "options":    q.get("options") if q.get("type") == "mcq" else None,
                "difficulty": q.get("difficulty", "medium") if q.get("difficulty") in ("easy", "medium", "hard") else "medium",
            })
        logger.info("Quiz generator — generated %d valid questions", len(valid))
        return valid
    except Exception as e:
        logger.error(
            "Quiz generator — LLM question generation failed: %s\n%s",
            e, traceback.format_exc()
        )
        return []


async def translate_questions(questions: list[dict], language: str) -> list[dict]:
    """Translate questions to Tamil or Hindi using LLM."""
    if not questions or language not in ("ta", "hi"):
        return questions

    prompt_tmpl = _TRANSLATE_PROMPT_TA if language == "ta" else _TRANSLATE_PROMPT_HI
    # Add temp id for merging
    to_translate = [{"id": q["idx"], **q} for q in questions]
    prompt = prompt_tmpl.format(questions_json=json.dumps(to_translate, ensure_ascii=False))

    try:
        raw = await _call_llm(prompt, timeout=120)
        translated = _extract_json_array(raw)
        # Build lookup by id
        t_map = {t["id"]: t for t in translated if "id" in t}
        result = []
        for q in questions:
            t = t_map.get(q["idx"], {})
            result.append({
                **q,
                f"question_{language}": t.get("question", q["question"]),
                f"answer_{language}":   t.get("answer",   q["answer"]),
                f"options_{language}":  t.get("options",  q.get("options")),
            })
        return result
    except Exception as e:
        logger.error("Quiz generator — translation to %s failed: %s", language, e)
        return questions


def _get_or_create_topic(
    db: Session,
    topic_name: str,
    slug: str,
    knowledge_file_id: Optional[int] = None,
) -> int:
    """
    Get existing topic id or create a new one.
    Always updates knowledge_file_id so re-uploads re-link correctly.
    Returns topic id.
    """
    row = fetch_one(db, "SELECT id FROM quiz_topics WHERE slug = :slug", {"slug": slug})
    if row:
        # Re-link to current file if knowledge_file_id is provided
        if knowledge_file_id is not None:
            execute(
                db,
                "UPDATE quiz_topics SET knowledge_file_id = :fid, is_active = 1 WHERE id = :id",
                {"fid": knowledge_file_id, "id": row["id"]},
            )
        return row["id"]
    topic_id = execute(
        db,
        """INSERT INTO quiz_topics (knowledge_file_id, name, slug, description, is_active)
           VALUES (:fid, :name, :slug, :desc, 1)""",
        {"fid": knowledge_file_id, "name": topic_name,
         "slug": slug, "desc": f"Auto-generated from {topic_name}.md"},
    )
    logger.info("Quiz generator — created new topic '%s' (id=%s, file_id=%s)",
                topic_name, topic_id, knowledge_file_id)
    return topic_id


def _insert_questions(db: Session, topic_id: int, questions: list[dict]) -> int:
    """Insert questions into quiz_questions table. Returns count inserted."""
    count = 0
    for q in questions:
        options_en = json.dumps(q["options"], ensure_ascii=False) if q.get("options") else None
        options_ta = json.dumps(q.get("options_ta"), ensure_ascii=False) if q.get("options_ta") else None
        options_hi = json.dumps(q.get("options_hi"), ensure_ascii=False) if q.get("options_hi") else None

        execute(db, """
            INSERT INTO quiz_questions
                (topic_id, question, question_ta, question_hi,
                 type, options, options_ta, options_hi,
                 answer, answer_ta, answer_hi, difficulty, is_active)
            VALUES
                (:tid, :q, :q_ta, :q_hi,
                 :type, :opts, :opts_ta, :opts_hi,
                 :ans, :ans_ta, :ans_hi, :diff, 1)
        """, {
            "tid":     topic_id,
            "q":       q["question"],
            "q_ta":    q.get("question_ta"),
            "q_hi":    q.get("question_hi"),
            "type":    q["type"],
            "opts":    options_en,
            "opts_ta": options_ta,
            "opts_hi": options_hi,
            "ans":     q["answer"],
            "ans_ta":  q.get("answer_ta"),
            "ans_hi":  q.get("answer_hi"),
            "diff":    q["difficulty"],
        })
        count += 1
    return count


# ── Main Entry Point ──────────────────────────────────────────

async def generate_and_store_questions(
    md_path: Path,
    db: Session,
    knowledge_file_id: Optional[int] = None,
) -> dict:
    """
    Full pipeline:
      1. Read .md file
      2. Generate questions via LLM
      3. Translate to Tamil + Hindi
      4. Store in MySQL (deletes old questions for this topic first on re-upload)

    knowledge_file_id: the ID of the knowledge_files row for this .md file.
    When provided, the quiz topic is linked to it so deleting the file
    auto-deletes the topic + questions via ON DELETE CASCADE.

    Returns summary dict with counts.
    """
    filename = md_path.name
    topic_name = md_path.stem.replace("_", " ").replace("-", " ").title()
    slug = md_path.stem.lower().replace("_", "-")

    logger.info("Quiz generator — starting for '%s' (knowledge_file_id=%s)",
                filename, knowledge_file_id)

    # 1. Read content
    try:
        content = md_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error("Quiz generator — could not read %s: %s", filename, e)
        return {"status": "error", "message": str(e)}

    if not content.strip():
        return {"status": "skipped", "message": "Empty file"}

    # 2. Generate questions
    questions = await generate_questions_from_content(content)
    if not questions:
        return {"status": "error", "message": "LLM failed to generate questions"}

    # 3. Translate to Tamil
    questions = await translate_questions(questions, "ta")

    # 4. Translate to Hindi
    questions = await translate_questions(questions, "hi")

    # 5. Get or create quiz topic (linked to knowledge_file_id)
    topic_id = _get_or_create_topic(db, topic_name, slug, knowledge_file_id)

    # 6. Delete OLD questions for this topic before re-inserting
    #    This ensures re-uploading a file replaces stale questions cleanly.
    from db.mysql import execute as db_execute
    db_execute(db, "DELETE FROM quiz_questions WHERE topic_id = :tid", {"tid": topic_id})
    logger.info("Quiz generator — cleared old questions for topic_id=%s before re-insert", topic_id)

    # 7. Insert into MySQL
    inserted = _insert_questions(db, topic_id, questions)

    logger.info(
        "Quiz generator — ✅ %d questions inserted for topic '%s' (id=%s, file_id=%s)",
        inserted, topic_name, topic_id, knowledge_file_id,
    )
    return {
        "status":    "ok",
        "topic":     topic_name,
        "topic_id":  topic_id,
        "inserted":  inserted,
    }
