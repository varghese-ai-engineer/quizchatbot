"""
Quiz Router — /api/quiz
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import httpx
import json

from config import settings
from db.mysql import execute, fetch_all, fetch_one, get_db
from models.schemas import QuizAnswerRequest, QuizStartRequest
from services.answer_evaluator import evaluate_open_answer, evaluate_mcq_answer

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Helpers ───────────────────────────────────────────────────

def _get_config(db: Session) -> dict:
    cfg = fetch_one(db, "SELECT * FROM quiz_config WHERE id = 1", {})
    return cfg or {
        "num_questions": 10,
        "marks_per_q": 1,
        "pass_mark_pct": 60,
        "question_type": "both",
        "intro_text": "Welcome to the Quiz!",
        "fuzzy_accept_threshold": 85,
        "fuzzy_reject_threshold": 55,
    }


# Words that indicate a line is NOT a rule instruction (e.g. leaked question text).
_RULE_REJECT_FIRST_WORDS = frozenset(["question"])


def _is_valid_rule_line(line: str) -> bool:
    """Return True if the line looks like a genuine rule instruction.

    Acceptance criteria (all must pass):
      1. The first character is ASCII alpha or a digit.
      2. The first word is not in _RULE_REJECT_FIRST_WORDS (e.g. "question").
      3. The line is NOT predominantly non-ASCII — i.e. the count of non-ASCII
         characters (excluding spaces) must not exceed the count of ASCII
         alphanumeric characters.  This catches lines like:
           'IPL-ல் யாரை Captain Cool-ன்னு சொல்வாங்க?'
         that start with ASCII letters but are mostly Tamil script.
    """
    stripped = line.strip()
    if not stripped:
        return False
    first_char = stripped[0]
    # Rule 1: must start with ASCII alpha or digit
    if not (first_char.isascii() and (first_char.isalpha() or first_char.isdigit())):
        return False
    # Rule 2: first word must not be a rejected sentinel
    first_word = stripped.split()[0].rstrip(".,:").lower()
    if first_word in _RULE_REJECT_FIRST_WORDS:
        return False
    # Rule 3: must not be predominantly non-ASCII content
    ascii_count = sum(1 for c in stripped if c.isascii() and c.isalnum())
    non_ascii_count = sum(1 for c in stripped if not c.isascii())
    if non_ascii_count > ascii_count:
        return False
    return True


def _get_lang_rules(db: Session) -> str:
    """Fetch ai_language_rules from the first indexed cricket knowledge file.

    Sanitizes the stored rules to strip any stray lines that are not
    rule instructions — e.g. translated question text that may have leaked
    into the DB field.

    A valid rule line must pass _is_valid_rule_line():
      • Starts with a digit (numbered rules like "1. Keep …"), or
      • Starts with an ASCII alpha character whose first word is not
        a banned sentinel (e.g. "question …").
    Lines beginning with Tamil/Hindi script are always rejected.
    """
    row = fetch_one(db,
        "SELECT ai_language_rules FROM knowledge_files "
        "WHERE status = 'indexed' AND domain_name = 'cricket' "
        "LIMIT 1", {})
    if row and row.get("ai_language_rules"):
        raw_rules = row["ai_language_rules"]
        sanitized_lines = [
            line for line in raw_rules.splitlines()
            if _is_valid_rule_line(line)
        ]
        if sanitized_lines:
            return "\n".join(sanitized_lines)
    # Fallback if nothing in DB or all lines were stripped
    return (
        "Keep all player names in English exactly as written.\n"
        "Keep all team names/abbreviations in English (CSK, MI, RCB, KKR etc.).\n"
        "Keep numbers, dates, and statistics in their original form."
    )


LANG_NAMES = {"en": "English", "ta": "Tamil", "hi": "Hindi"}

# Language-aware MCQ feedback — avoids hardcoded English strings
_MCQ_CORRECT: dict[str, str] = {
    "en": "Correct!",
    "ta": "சரி!",
    "hi": "सही!",
}
_MCQ_INCORRECT: dict[str, str] = {
    "en": "Incorrect. The correct answer is: {answer}",
    "ta": "தவறு. சரியான answer: {answer}",
    "hi": "गलत. सही answer: {answer}",
}


async def _translate_questions(questions: list[dict], language: str, lang_rules: str) -> list[dict]:
    """Batch-translate quiz questions to the target language using LLM.
    Returns translated questions; falls back to originals on failure."""
    if language == "en":
        return questions

    lang_name = LANG_NAMES.get(language, "English")

    # Build compact JSON for translation
    to_translate = [
        {
            "id":         q["id"],
            "question":   q["question"],
            "answer":     q["answer"],
            "type":       q["type"],
            "difficulty": q["difficulty"],
            "options":    q.get("options"),  # list or None
        }
        for q in questions
    ]

    # Build language-specific translation instructions
    if language == "ta":
        lang_instruction = (
            "Translate to SIMPLE, SPOKEN Tamil (\u0ba4\u0bae\u0bbf\u0bb4\u0bcd) mixed with English words.\n\n"
            "STRICT RULES:\n"
            "1. Keep ALL player names in ENGLISH script: Chris Gayle, Virat Kohli, MS Dhoni (NEVER transliterate into Tamil script)\n"
            "2. Keep ALL team names in ENGLISH: CSK, MI, RCB, KKR (NEVER write in Tamil script)\n"
            "3. Keep ALL numbers in ENGLISH: 175*, 358, 2013 (NEVER convert to Tamil numerals)\n"
            "4. Use simple spoken Tamil for the question and answer text\n"
            "5. Do NOT use formal or literary Tamil\n"
            "6. Do NOT transliterate English words into Tamil script \u2014 keep them in English\n\n"
            "CORRECT translation example:\n"
            '  English: "Who has scored the most runs in IPL history?"\n'
            '  Tamil:   "IPL history-\u0bb2\u0bcd \u0b85\u0ba4\u0bbf\u0b95 runs \u0baf\u0bbe\u0bb0\u0bcd \u0b85\u0b9f\u0bbf\u0b9a\u0bcd\u0b9a\u0bbe\u0b99\u0bcd\u0b95?"\n\n'
            "WRONG translation (DO NOT DO THIS):\n"
            '  "\u0b90.\u0baa\u0bbf.\u0b8f\u0bb2\u0bcd. \u0bb5\u0bb0\u0bb2\u0bbe\u0bb1\u0bcd\u0bb1\u0bbf\u0bb2\u0bcd \u0b85\u0ba4\u0bbf\u0b95\u0bae\u0bbe\u0ba9 \u0b93\u0b9f\u0bcd\u0b9f\u0b99\u0bcd\u0b95\u0bb3\u0bcd \u0baf\u0bbe\u0bb0\u0bcd \u0b8e\u0b9f\u0bc1\u0ba4\u0bcd\u0ba4\u0ba9\u0bb0\u0bcd?"\n\n'
            "Follow the CORRECT example style exactly.\n"
        )
    elif language == "hi":
        lang_instruction = (
            "Translate to SIMPLE, SPOKEN Hindi mixed with English words.\n\n"
            "STRICT RULES:\n"
            "1. Keep ALL player names in ENGLISH script: Chris Gayle, Virat Kohli, MS Dhoni (NEVER transliterate into Hindi/Devanagari)\n"
            "2. Keep ALL team names in ENGLISH: CSK, MI, RCB, KKR (NEVER write in Hindi script)\n"
            "3. Keep ALL numbers in ENGLISH: 175*, 358, 2013\n"
            "4. Use simple spoken Hindi for the question and answer text\n"
            "5. Do NOT use formal or literary Hindi\n"
            "6. Do NOT transliterate English words into Hindi script \u2014 keep them in English\n\n"
            "CORRECT translation example:\n"
            '  English: "Who has scored the most runs in IPL history?"\n'
            '  Hindi:   "IPL history \u092e\u0947\u0902 \u0938\u092c\u0938\u0947 \u091c\u093c\u094d\u092f\u093e\u0926\u093e runs \u0915\u093f\u0938\u0928\u0947 \u092c\u0928\u093e\u090f?"\n\n'
            "WRONG translation (DO NOT DO THIS):\n"
            '  "\u0906\u0908.\u092a\u0940.\u090f\u0932. \u0907\u0924\u093f\u0939\u093e\u0938 \u092e\u0947\u0902 \u0938\u0930\u094d\u0935\u093e\u0927\u093f\u0915 \u0930\u0928 \u0915\u093f\u0938\u0928\u0947 \u092c\u0928\u093e\u090f?"\n\n'
            "Follow the CORRECT example style exactly.\n"
        )
    else:
        lang_instruction = f"Translate to {lang_name}.\n"

    prompt = (
        f"You are a quiz translator. Translate these IPL cricket quiz questions and answers "
        f"from English to {lang_name}.\n\n"
        f"{lang_instruction}\n"
        f"Additional language rules:\n{lang_rules}\n\n"
        f"IMPORTANT:\n"
        f"- Translate ONLY the 'question', 'answer', and 'options' fields.\n"
        f"- Keep 'id', 'type', 'difficulty' EXACTLY the same.\n"
        f"- For 'options': translate each option string in the array.\n"
        f"- Return ONLY valid JSON \u2014 no explanation, no markdown, no extra text.\n"
        f"- CRITICAL: Keep ALL names, numbers, and team names in English script. Do NOT transliterate.\n\n"
        f"Questions JSON:\n{json.dumps(to_translate, ensure_ascii=False)}\n\n"
        f"Return translated JSON array:"
    )
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{settings.ollama_host}/api/generate",
                json={"model": settings.llm_model, "prompt": prompt, "stream": False},
            )
            r.raise_for_status()
            raw = r.json().get("response", "").strip()

        # Extract JSON array from response
        start = raw.find("[")
        end   = raw.rfind("]") + 1
        if start == -1 or end == 0:
            return questions  # fallback to English

        translated = json.loads(raw[start:end])

        # Merge translated fields back into original question dicts
        translated_map = {t["id"]: t for t in translated}
        result = []
        for q in questions:
            t = translated_map.get(q["id"], {})
            result.append({
                **q,
                "question": t.get("question", q["question"]),
                "answer":   t.get("answer",   q["answer"]),
                "options":  t.get("options",  q.get("options")),
            })
        return result

    except Exception:
        return questions  # fallback to English on any error


def _sanitize_feedback(feedback: str, is_correct: bool, language: str) -> str:
    """
    Programmatically sanitizes feedback returned by the LLM.
    Ensures that correct/incorrect status terms in feedback align with the evaluation verdict
    and strips any contradictory prefixes.
    """
    feedback = feedback.strip()
    if not feedback:
        return feedback

    if language == "ta":
        if is_correct:
            # Correct verdict must not start with wrong-related terms.
            # e.g., "சரியான தவறை", "சரியான தவறு", "தவறு"
            for prefix in ["சரியான தவறை", "சரியான தவறு", "தவறு"]:
                if feedback.startswith(prefix):
                    feedback = feedback[len(prefix):].lstrip("!.,:; ")
                    break
            # Ensure it starts with "சரி!"
            if not feedback.startswith("சரி"):
                feedback = f"சரி! {feedback}"
        else:
            # Incorrect verdict must not start with correct-related terms.
            # e.g., "சரியான தவறை" is wrong anyway, but if it starts with "சரி" or "சரியான"
            for prefix in ["சரியான தவறை", "சரியான தவறு", "சரியான பதில்", "சரியான", "சரி"]:
                if feedback.startswith(prefix):
                    feedback = feedback[len(prefix):].lstrip("!.,:; ")
                    break
            # Ensure it starts with "தவறு."
            if not feedback.startswith("தவறு"):
                feedback = f"தவறு. {feedback}"

    elif language == "hi":
        if is_correct:
            if feedback.startswith("गलत"):
                feedback = feedback[len("गलत"):].lstrip("!.,:; ")
            if not feedback.startswith("सही"):
                feedback = f"सही! {feedback}"
        else:
            for prefix in ["सही जवाब", "सही", "सहीं"]:
                if feedback.startswith(prefix):
                    feedback = feedback[len(prefix):].lstrip("!.,:; ")
                    break
            if not feedback.startswith("गलत"):
                feedback = f"गलत. {feedback}"

    elif language == "en":
        lower_feedback = feedback.lower()
        if is_correct:
            for prefix in ["incorrect", "wrong"]:
                if lower_feedback.startswith(prefix):
                    feedback = feedback[len(prefix):].lstrip("!.,:; ")
                    break
            if not feedback.lower().startswith("correct"):
                feedback = f"Correct! {feedback}"
        else:
            for prefix in ["correct", "right"]:
                if lower_feedback.startswith(prefix):
                    feedback = feedback[len(prefix):].lstrip("!.,:; ")
                    break
            if not feedback.lower().startswith("incorrect") and not feedback.lower().startswith("wrong"):
                feedback = f"Incorrect. {feedback}"

    return feedback


        is_correct = user_answer.strip().lower() == correct_answer.strip().lower()
        fallback_feedback = "Auto-evaluated." if is_correct else f"Correct answer: {correct_answer}"
        return is_correct, _sanitize_feedback(fallback_feedback, is_correct, language)

# ── Endpoints ─────────────────────────────────────────────────

@router.get("/config")
def get_quiz_config(db: Session = Depends(get_db)) -> dict:
    """Return current quiz config (for intro screen)."""
    cfg = _get_config(db)
    total_marks = cfg["num_questions"] * cfg["marks_per_q"]
    pass_marks  = round(total_marks * cfg["pass_mark_pct"] / 100)
    return {**cfg, "total_marks": total_marks, "pass_marks": pass_marks}


@router.get("/history/{user_id}")
def get_quiz_history(user_id: int, db: Session = Depends(get_db)) -> dict:
    """Return all completed quiz sessions for a user, newest first."""
    sessions = fetch_all(db, """
        SELECT
            qs.id, qs.score, qs.total_questions,
            qs.marks_per_q, qs.pass_mark_pct,
            qs.started_at,
            COALESCE(qt.name, 'All Topics') AS topic_name
        FROM quiz_sessions qs
        LEFT JOIN quiz_topics qt ON qs.topic_id = qt.id
        WHERE qs.user_id = :uid AND qs.completed = 1
        ORDER BY qs.started_at DESC
    """, {"uid": user_id})

    results = []
    for s in sessions:
        earned  = s["score"] * s["marks_per_q"]
        total   = s["total_questions"] * s["marks_per_q"]
        pass_m  = round(total * s["pass_mark_pct"] / 100)
        pct     = round((earned / total) * 100) if total else 0
        results.append({
            **s,
            "earned_marks": earned,
            "total_marks":  total,
            "pass_marks":   pass_m,
            "percentage":   pct,
            "passed":       earned >= pass_m,
        })
    return {"sessions": results}


@router.get("/topics")
async def list_topics(db: Session = Depends(get_db)) -> list[dict]:
    """Only return topics that have at least one active question."""
    return fetch_all(db, """
        SELECT qt.id, qt.name, qt.slug, qt.description, COUNT(qq.id) AS question_count
        FROM quiz_topics qt
        JOIN quiz_questions qq ON qt.id = qq.topic_id AND qq.is_active = 1
        WHERE qt.is_active = 1
        GROUP BY qt.id, qt.name, qt.slug, qt.description
        ORDER BY question_count DESC
    """, {})


@router.post("/start")
async def start_quiz(body: QuizStartRequest, db: Session = Depends(get_db)) -> dict:
    cfg = _get_config(db)
    lang_rules = _get_lang_rules(db)  # fetch from knowledge_files DB

    topic_filter_sql = ""
    params: dict = {"lim": cfg["num_questions"]}

    if body.topic_slug == "all":
        base_where = "WHERE is_active = 1"
    else:
        topic = fetch_one(
            db,
            "SELECT id FROM quiz_topics WHERE slug = :slug AND is_active = 1 LIMIT 1",
            {"slug": body.topic_slug},
        )
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found.")
        base_where = "WHERE topic_id = :tid AND is_active = 1"
        params["tid"] = topic["id"]

    q_type = cfg["question_type"]
    if q_type == "both":
        sql = f"""SELECT id, question, question_ta, question_hi,
                         type, options, options_ta, options_hi,
                         difficulty, answer, answer_ta, answer_hi
                  FROM quiz_questions
                  {base_where}
                  ORDER BY RAND() LIMIT :lim"""
    else:
        params["qtype"] = q_type
        sql = f"""SELECT id, question, question_ta, question_hi,
                         type, options, options_ta, options_hi,
                         difficulty, answer, answer_ta, answer_hi
                  FROM quiz_questions
                  {base_where} AND type = :qtype
                  ORDER BY RAND() LIMIT :lim"""

    questions = fetch_all(db, sql, params)
    if not questions:
        raise HTTPException(status_code=404, detail="No questions available for this topic.")

    topic_id_for_session = params.get("tid", None)
    session_id = execute(
        db,
        """INSERT INTO quiz_sessions (user_id, topic_id, total_questions, marks_per_q, pass_mark_pct)
           VALUES (:uid, :tid, :total, :mpq, :pmp)""",
        {
            "uid": body.user_id,
            "tid": topic_id_for_session,
            "total": len(questions),
            "mpq": cfg["marks_per_q"],
            "pmp": cfg["pass_mark_pct"],
        },
    )

    # Parse MCQ options JSON
    for q in questions:
        if q["options"]:
            q["options"] = json.loads(q["options"]) if isinstance(q["options"], str) else q["options"]
        if q.get("options_ta"):
            q["options_ta"] = json.loads(q["options_ta"]) if isinstance(q["options_ta"], str) else q["options_ta"]
        if q.get("options_hi"):
            q["options_hi"] = json.loads(q["options_hi"]) if isinstance(q["options_hi"], str) else q["options_hi"]

    # Apply pre-translated columns if language != 'en'
    if body.language != "en":
        lang_suffix = f"_{body.language}"  # e.g. "_ta" or "_hi"
        needs_llm_translation = []
        for q in questions:
            q_translated = q.get(f"question{lang_suffix}")
            a_translated = q.get(f"answer{lang_suffix}")
            o_translated = q.get(f"options{lang_suffix}")
            if q_translated:
                # Use pre-translated version from DB
                q["question"] = q_translated
                if a_translated:
                    q["answer"] = a_translated
                if o_translated:
                    q["options"] = o_translated
            else:
                # No pre-translation — collect for LLM fallback
                needs_llm_translation.append(q)

        # LLM fallback only for questions missing DB translations
        if needs_llm_translation:
            logger.info("Quiz — %d/%d questions need LLM translation to %s",
                        len(needs_llm_translation), len(questions), body.language)
            translated = await _translate_questions(needs_llm_translation, body.language, lang_rules)
            translated_map = {t["id"]: t for t in translated}
            for q in questions:
                if q["id"] in translated_map:
                    t = translated_map[q["id"]]
                    q["question"] = t.get("question", q["question"])
                    q["answer"] = t.get("answer", q["answer"])
                    if t.get("options"):
                        q["options"] = t["options"]

    # Clean up translation columns before sending to frontend
    for q in questions:
        for key in ["question_ta", "question_hi", "answer_ta", "answer_hi", "options_ta", "options_hi"]:
            q.pop(key, None)

    # Strip answer from questions sent to frontend (keep for evaluation server-side)
    frontend_questions = [
        {k: v for k, v in q.items() if k != "answer"}
        for q in questions
    ]

    return {
        "quiz_session_id": session_id,
        "questions": frontend_questions,
        "config": {
            "marks_per_q": cfg["marks_per_q"],
            "pass_mark_pct": cfg["pass_mark_pct"],
            "total_marks": len(questions) * cfg["marks_per_q"],
        },
    }


@router.post("/answer")
async def submit_answer(body: QuizAnswerRequest, db: Session = Depends(get_db)) -> dict:
    question = fetch_one(
        db,
        "SELECT question, type, answer, answer_ta, answer_hi FROM quiz_questions WHERE id = :qid LIMIT 1",
        {"qid": body.question_id},
    )
    if not question:
        raise HTTPException(status_code=404, detail="Question not found.")

    session = fetch_one(
        db,
        "SELECT marks_per_q FROM quiz_sessions WHERE id = :sid LIMIT 1",
        {"sid": body.quiz_session_id},
    )
    marks_per_q = session["marks_per_q"] if session else 1

    # MCQ: exact match; open: semantic evaluation
    cfg        = _get_config(db)
    lang_rules = _get_lang_rules(db)

    # Pick the language-appropriate correct answer for MCQ comparison and feedback.
    # answer_ta / answer_hi may be None if not yet translated — fall back to English.
    lang_answer_col = f"answer_{body.language}" if body.language != "en" else None
    localized_answer = (
        question.get(lang_answer_col) or question["answer"]
        if lang_answer_col
        else question["answer"]
    )

    if question["type"] == "mcq":
        # Strict exact match — options are shown on screen, no semantic eval needed
        is_correct = evaluate_mcq_answer(body.user_answer, localized_answer)
        eval_method = "mcq_exact"
        lang = body.language if body.language in _MCQ_CORRECT else "en"
        if is_correct:
            feedback = _MCQ_CORRECT[lang]
        else:
            feedback = _MCQ_INCORRECT[lang].format(answer=localized_answer)
    else:
        # Load aliases for this correct answer from answer_aliases table
        alias_rows = fetch_all(
            db,
            "SELECT alias FROM answer_aliases WHERE canonical = :canonical",
            {"canonical": question["answer"]},
        )
        aliases = [r["alias"] for r in alias_rows] if alias_rows else []

        # Load fuzzy thresholds from quiz_config (fallback to safe defaults)
        fuzzy_accept = int(cfg.get("fuzzy_accept_threshold") or 85)
        fuzzy_reject = int(cfg.get("fuzzy_reject_threshold") or 55)

        # Always evaluate against English canonical answer (MySQL source of truth)
        is_correct, feedback, eval_method = await evaluate_open_answer(
            question=question["question"],
            correct_answer=question["answer"],   # English canonical
            user_answer=body.user_answer,
            language=body.language,
            lang_rules=lang_rules,
            aliases=aliases,
            fuzzy_accept=fuzzy_accept,
            fuzzy_reject=fuzzy_reject,
        )

    execute(
        db,
        """INSERT INTO quiz_answers (quiz_session_id, question_id, user_answer, is_correct)
           VALUES (:sid, :qid, :answer, :correct)""",
        {
            "sid": body.quiz_session_id,
            "qid": body.question_id,
            "answer": body.user_answer,
            "correct": int(is_correct),
        },
    )

    if is_correct:
        execute(
            db,
            "UPDATE quiz_sessions SET score = score + 1 WHERE id = :sid",
            {"sid": body.quiz_session_id},
        )

    # Build debug prompt string (for admin popup)
    debug_row  = fetch_one(db, "SELECT show_prompt_debug FROM global_ai_settings WHERE id=1", {})
    show_debug = bool(debug_row["show_prompt_debug"]) if debug_row else False

    debug_prompt = None
    if show_debug and question["type"] == "open":
        lang_name = {"en": "English", "ta": "Tamil", "hi": "Hindi"}.get(body.language, "English")
        debug_prompt = (
            f"=== QUIZ EVALUATION ===\n"
            f"Method:         {eval_method}\n"
            f"Question:       {question['question']}\n"
            f"Correct Answer: {question['answer']}\n"
            f"Student Answer: {body.user_answer}\n"
            f"Language:       {lang_name}\n"
            f"Aliases loaded: {aliases if question['type'] == 'open' else 'N/A (MCQ)'}\n"
            f"Fuzzy thresholds: accept>={fuzzy_accept if question['type'] == 'open' else 'N/A'} "
            f"reject<{fuzzy_reject if question['type'] == 'open' else 'N/A'}"
        )

    return {
        "is_correct":     is_correct,
        "correct_answer": question["answer"],
        "feedback":       feedback,
        "marks_awarded":  marks_per_q if is_correct else 0,
        "eval_method":    eval_method,
        "debug_prompt":   debug_prompt,
    }


@router.post("/finish/{session_id}")
async def finish_quiz(session_id: int, db: Session = Depends(get_db)) -> dict:
    session = fetch_one(
        db,
        "SELECT * FROM quiz_sessions WHERE id = :sid LIMIT 1",
        {"sid": session_id},
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    execute(
        db,
        "UPDATE quiz_sessions SET completed = 1, ended_at = NOW() WHERE id = :sid",
        {"sid": session_id},
    )

    score       = session["score"]
    total       = session["total_questions"]
    marks_per_q = session["marks_per_q"]
    pass_pct    = session["pass_mark_pct"]

    earned_marks = score * marks_per_q
    total_marks  = total * marks_per_q
    pass_marks   = round(total_marks * pass_pct / 100)
    percentage   = round((earned_marks / total_marks) * 100) if total_marks else 0
    passed       = earned_marks >= pass_marks

    return {
        "score":        score,
        "total":        total,
        "earned_marks": earned_marks,
        "total_marks":  total_marks,
        "pass_marks":   pass_marks,
        "percentage":   percentage,
        "passed":       passed,
        "message": (
            f"🎉 Passed! You scored {earned_marks}/{total_marks} ({percentage}%)"
            if passed else
            f"❌ Failed. You scored {earned_marks}/{total_marks} ({percentage}%). Need {pass_marks} to pass."
        ),
    }
