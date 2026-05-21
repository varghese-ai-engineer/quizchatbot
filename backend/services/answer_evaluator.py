"""
Answer Evaluator Service  (domain-agnostic)
===========================================

6-Stage evaluation pipeline for open-ended quiz answers.
No domain-specific keywords anywhere in this file.

Stage 0  — Alias lookup        (DB-driven, instant accept)
Stage 1  — Normalize           (lowercase, strip punctuation, drop fillers)
Stage 1.5— Acronym match       (CSK↔Chennai Super Kings, instant accept)
Stage 2  — Exact match         (post-normalisation)
Stage 3  — Fuzzy match         (RapidFuzz token_set_ratio, configurable thresholds)
Stage 4  — LLM semantic check  (YES/NO only, domain-agnostic prompt, uncertain zone only)
Feedback — Generated separately after verdict is known (no contradiction risk)

MCQ evaluation:  strict exact match only  (separate function, stages 0-4 not used)
"""
from __future__ import annotations

import logging
import re
import unicodedata
from typing import Optional

import httpx
from rapidfuzz import fuzz

from config import settings

logger = logging.getLogger(__name__)

# ── Language helpers ──────────────────────────────────────────────────────────
LANG_NAMES = {"en": "English", "ta": "Tamil", "hi": "Hindi"}

# ── Generic filler words stripped during normalization ────────────────────────
# Keep this list SMALL and truly domain-agnostic — articles, prepositions, copulas.
# Do NOT add domain words (cricket, ipl, stadium…) — those vary by knowledge file.
_FILLER = frozenset({
    "the", "a", "an", "of", "in", "at", "on", "and", "or",
    "is", "was", "are", "were", "be", "been", "being",
})


# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — Normalization
# ─────────────────────────────────────────────────────────────────────────────

def normalize(text: str) -> str:
    """
    Normalize answer text for comparison:
      1. Unicode NFC
      2. Lowercase
      3. Collapse dotted/hyphenated abbreviations:  M.S. → ms,  C.S.K. → csk,  M-S → ms
      4. Remove remaining non-alphanumeric characters
      5. Drop generic filler words
      6. Collapse whitespace

    Examples:
      "M. A. Chidambaram Stadium" → "chidambaram stadium"
      "M.S. Dhoni"               → "ms dhoni"
      "C.S.K."                   → "csk"
      "MS Dhoni"                 → "ms dhoni"
      "Rajasthan Royals (RR)"    → "rajasthan royals rr"
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = text.lower()
    # Step 3a: collapse X.Y.Z. patterns — remove dots between single letters so
    # "m.s." → "ms" and "c.s.k." → "csk" and "m.a." → "ma"
    # Pattern: a single letter followed by dot (with optional following letter)
    text = re.sub(r"(?<=[a-z])\.", "", text)   # remove dot after single letter
    # Step 3b: collapse hyphen between letters: M-S → ms (already lowercase)
    text = re.sub(r"([a-z])-([a-z])", r"\1\2", text)
    # Step 4: replace remaining non-alphanumeric with space
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    # Step 5: drop filler words
    tokens = [t for t in text.split() if t not in _FILLER]
    return " ".join(tokens).strip()


# ─────────────────────────────────────────────────────────────────────────────
# Stage 1.5 — Acronym match
# ─────────────────────────────────────────────────────────────────────────────

def _acronym(text: str) -> str:
    """
    Return the initialism of a normalized multi-word string.
    Single-word inputs return "" (no meaningful acronym).

    "chennai super kings" → "csk"
    "ms dhoni"            → "md"   (not useful — 2 letters match many things)
    "rajasthan royals"    → "rr"
    """
    words = normalize(text).split()
    if len(words) < 2:
        return ""
    return "".join(w[0] for w in words)


def acronym_match(user_answer: str, correct_answer: str) -> bool:
    """
    Return True if either answer is the initialism of the other.

    Checks both directions:
      user="CSK",  correct="Chennai Super Kings" → True  (normalize(user)=="csk" == acronym(correct))
      user="Chennai Super Kings", correct="CSK"  → True  (acronym(user)=="csk" == normalize(correct))
    """
    n_user    = normalize(user_answer)
    n_correct = normalize(correct_answer)

    acr_correct = _acronym(correct_answer)
    acr_user    = _acronym(user_answer)

    # user typed the acronym of the canonical answer
    if acr_correct and n_user == acr_correct:
        return True
    # user typed the full form of a canonical acronym
    if acr_user and acr_user == n_correct:
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — Exact match (post-normalization)
# ─────────────────────────────────────────────────────────────────────────────

def exact_match(user_answer: str, correct_answer: str) -> bool:
    """Return True if normalised answers are identical."""
    return normalize(user_answer) == normalize(correct_answer)


# ─────────────────────────────────────────────────────────────────────────────
# Stage 3 — Fuzzy match
# ─────────────────────────────────────────────────────────────────────────────

def fuzzy_score(user_answer: str, correct_answer: str) -> int:
    """
    RapidFuzz token_set_ratio on normalised strings.
    token_set_ratio is chosen because it:
      - Ignores word order  ("Dhoni MS" == "MS Dhoni")
      - Handles partial names ("Dhoni" ≈ "MS Dhoni")
      - Robust to extra or missing words
    Returns 0–100.
    """
    n_user    = normalize(user_answer)
    n_correct = normalize(correct_answer)
    if not n_user or not n_correct:
        return 0
    return int(fuzz.token_set_ratio(n_user, n_correct))


def fuzzy_match(
    user_answer: str,
    correct_answer: str,
    accept_threshold: int = 85,
    reject_threshold: int = 55,
) -> tuple[Optional[bool], int]:
    """
    Returns (decision, score):
      True  — confident CORRECT (score >= accept_threshold)
      False — confident WRONG   (score <  reject_threshold)
      None  — uncertain zone; escalate to LLM semantic check
    """
    score = fuzzy_score(user_answer, correct_answer)
    if score >= accept_threshold:
        return True, score
    if score < reject_threshold:
        return False, score
    return None, score


# ─────────────────────────────────────────────────────────────────────────────
# Stage 0 — Alias lookup  (called first despite lower stage number)
# ─────────────────────────────────────────────────────────────────────────────

def alias_match(user_answer: str, aliases: list[str]) -> bool:
    """
    Return True if the normalized user answer matches any stored alias.
    Aliases are loaded from the answer_aliases table by the caller (quiz.py)
    and passed in — this function has no DB dependency.

    Case-insensitive, punctuation-insensitive.
    """
    if not aliases:
        return False
    n_user = normalize(user_answer)
    return any(normalize(a) == n_user for a in aliases)


# ─────────────────────────────────────────────────────────────────────────────
# Stage 4 — LLM semantic equivalence check  (YES/NO only, domain-agnostic)
# ─────────────────────────────────────────────────────────────────────────────

async def llm_semantic_check(
    question: str,
    correct_answer: str,
    user_answer: str,
) -> bool:
    """
    Domain-agnostic YES/NO semantic equivalence check.

    The prompt contains ZERO hardcoded domain examples.
    It reasons generically about abbreviations, nicknames, partial names,
    and aliases — regardless of the subject domain.

    Returns True if YES, False if NO or on any LLM/network error.
    """
    prompt = (
        f"You are a quiz answer evaluator.\n"
        f"Question: {question}\n"
        f"Correct Answer: {correct_answer}\n"
        f"Student Answer: {user_answer}\n\n"
        "Task: Determine whether the student's answer clearly refers to the\n"
        "same real-world entity (person, place, organization, concept, or event)\n"
        "as the correct answer.\n\n"
        "ACCEPT (answer YES) if any of these are true:\n"
        "  - The student answer is a well-known abbreviation of the correct answer\n"
        "  - The student answer is a widely-used nickname or alias\n"
        "  - The student answer is a partial name that unambiguously identifies the correct answer\n"
        "  - The core factual meaning is the same even if phrased differently\n\n"
        "REJECT (answer NO) if:\n"
        "  - The student answer refers to a clearly different entity\n"
        "  - The student answer is factually wrong\n"
        "  - The student answer is too vague or ambiguous to be accepted\n\n"
        "Reply with ONLY one word: YES or NO"
    )
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                f"{settings.ollama_host}/api/generate",
                json={"model": settings.llm_model, "prompt": prompt, "stream": False},
            )
            r.raise_for_status()
            raw = r.json().get("response", "").strip().upper()

        first_line = raw.splitlines()[0] if raw else ""
        is_yes = "YES" in first_line and "NO" not in first_line
        logger.debug("LLM semantic → %s  (raw: %r)", "YES" if is_yes else "NO", first_line)
        return is_yes

    except Exception as exc:
        logger.warning("LLM semantic check failed (%s) — defaulting NO", exc)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Feedback generation  (separate from verdict — no contradiction risk)
# ─────────────────────────────────────────────────────────────────────────────

def _lang_feedback_rules(language: str) -> str:
    if language == "ta":
        return (
            "Give feedback in SIMPLE, SPOKEN Tanglish — the natural Tamil+English mix that\n"
            "educated Indian users actually speak. NOT formal written Tamil.\n\n"
            "STRICT RULES:\n"
            "1. Keep ALL proper nouns, names, numbers, technical terms in ENGLISH script.\n"
            "2. NEVER transliterate English words into Tamil script.\n"
            "3. Use Tamil ONLY for verbs and connectors: தான், வென்றுள்ளார், சரியான, இல்ல, தான்.\n\n"
            "When answer is CORRECT — start with 'சரி!' then ONE Tanglish sentence.\n"
            "  Pattern: சரி! [student_answer] தான் correct — [brief fact in Tanglish].\n"
            "  Example: சரி! MS Dhoni தான் correct — 5 IPL titles வென்னுட்டாரு.\n"
            "  Example: சரி! Python தான் correct — interpreted language தான்.\n\n"
            "When answer is INCORRECT — start with 'தவறு.' then ONE Tanglish sentence.\n"
            "  Pattern: தவறு. Correct answer [correct_answer] தான், [brief reason].\n"
            "  Example: தவறு. Correct answer MS Dhoni தான், not Kohli.\n"
            "  Example: தவறு. Correct answer Python தான், not Java.\n\n"
            "BANNED (never write these):\n"
            "  இபிஎல் → always write IPL\n"
            "  திடல்களை / காலிகளை → always write titles\n"
            "  ஏப்பயங்களும் / மட்டுமே → meaningless filler, remove it\n"
        )
    if language == "hi":
        return (
            "Give feedback in SIMPLE, SPOKEN Hinglish — the natural Hindi+English mix\n"
            "that educated Indian users actually speak. NOT formal written Hindi.\n\n"
            "STRICT RULES:\n"
            "1. Keep ALL proper nouns, names, numbers, technical terms in ENGLISH script.\n"
            "2. NEVER transliterate English words into Hindi script.\n"
            "3. Use Hindi ONLY for verbs and connectors: है, हैं, था, ने, का, की.\n\n"
            "When answer is CORRECT — start with 'सही!' then ONE Hinglish sentence.\n"
            "  Example: सही! MS Dhoni ने 5 IPL titles जीते हैं.\n"
            "  Example: सही! Python ही correct answer है.\n\n"
            "When answer is INCORRECT — start with 'गलत.' then ONE Hinglish sentence.\n"
            "  Example: गलत. Correct answer MS Dhoni है, not Kohli.\n"
            "  Example: गलत. Correct answer Python है, Java नहीं.\n\n"
            "BANNED: आईपीएल → always write IPL\n"
        )
    lang = LANG_NAMES.get(language, "English")
    return f"Give feedback in {lang} in ONE short sentence.\n"


async def _generate_feedback(
    question: str,
    correct_answer: str,
    user_answer: str,
    is_correct: bool,
    language: str,
    lang_rules: str,
) -> str:
    """
    Generate one-sentence multilingual feedback.
    Verdict is passed in — the LLM cannot contradict it.
    """
    verdict_word = "correct" if is_correct else "incorrect"
    lang_rules_section = f"\nAdditional language rules:\n{lang_rules}\n" if lang_rules else ""

    prompt = (
        f"You are a quiz feedback generator.\n"
        f"Question: {question}\n"
        f"Correct Answer: {correct_answer}\n"
        f"Student Answer: {user_answer}\n"
        f"Evaluation Verdict: {verdict_word}\n\n"
        f"{_lang_feedback_rules(language)}"
        f"{lang_rules_section}"
        "Write exactly ONE sentence of feedback for the student.\n"
        "The verdict is already decided — do NOT contradict it.\n"
        "Reply format:\n"
        "FEEDBACK: <one sentence>"
    )
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            r = await client.post(
                f"{settings.ollama_host}/api/generate",
                json={"model": settings.llm_model, "prompt": prompt, "stream": False},
            )
            r.raise_for_status()
            text = r.json().get("response", "").strip()

        for line in text.splitlines():
            if line.upper().startswith("FEEDBACK:"):
                return line.split(":", 1)[-1].strip()
        for line in text.splitlines():
            if line.strip():
                return line.strip()

    except Exception as exc:
        logger.warning("Feedback generation failed: %s", exc)

    # Canned fallback — guaranteed correct/wrong prefix per language
    if is_correct:
        return {
            "en": "Correct! Well done.",
            "ta": "சரி! நல்லா பண்ண!",
            "hi": "सही! शाबाश!",
        }.get(language, "Correct!")
    return {
        "en": f"Incorrect. The correct answer is: {correct_answer}",
        "ta": f"தவறு. correct answer: {correct_answer}",
        "hi": f"गलत. सही answer: {correct_answer}",
    }.get(language, f"Incorrect. Correct answer: {correct_answer}")


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def evaluate_open_answer(
    question: str,
    correct_answer: str,       # English canonical answer from MySQL
    user_answer: str,
    language: str = "en",
    lang_rules: str = "",
    aliases: Optional[list[str]] = None,          # from answer_aliases table
    fuzzy_accept: int = 85,                        # from quiz_config
    fuzzy_reject: int = 55,                        # from quiz_config
) -> tuple[bool, str, str]:
    """
    Main entry point for open-ended answer evaluation.

    Always evaluates against the English canonical correct_answer (MySQL source of truth).
    Translated answers are only used for displaying correct answer text in feedback.

    Returns: (is_correct, feedback_text, method_used)

    method_used values:
      'empty'          — blank submission
      'alias'          — matched a stored alias
      'acronym'        — matched via acronym normalization
      'exact'          — post-normalization exact match
      'fuzzy:<score>'  — fuzzy score >= accept threshold
      'fuzzy_reject:<score>' — fuzzy score < reject threshold (no LLM)
      'llm_semantic:<score>' — LLM semantic check (uncertain zone)
      'fallback'       — LLM unavailable, fell back to exact match
    """
    aliases = aliases or []

    # ── Guard: blank answer ───────────────────────────────────────────────
    if not user_answer or not user_answer.strip():
        fb = await _generate_feedback(
            question, correct_answer, user_answer, False, language, lang_rules
        )
        return False, fb, "empty"

    # ── Stage 0: Alias lookup ─────────────────────────────────────────────
    if alias_match(user_answer, aliases):
        logger.info("Eval alias ✅  %r in aliases", user_answer)
        fb = await _generate_feedback(
            question, correct_answer, user_answer, True, language, lang_rules
        )
        return True, fb, "alias"

    # ── Stage 1.5: Acronym match ──────────────────────────────────────────
    if acronym_match(user_answer, correct_answer):
        logger.info("Eval acronym ✅  %r ↔ %r", user_answer, correct_answer)
        fb = await _generate_feedback(
            question, correct_answer, user_answer, True, language, lang_rules
        )
        return True, fb, "acronym"

    # ── Stage 2: Exact match (post-normalisation) ─────────────────────────
    if exact_match(user_answer, correct_answer):
        logger.info("Eval exact ✅  %r == %r", user_answer, correct_answer)
        fb = await _generate_feedback(
            question, correct_answer, user_answer, True, language, lang_rules
        )
        return True, fb, "exact"

    # ── Stage 3: Fuzzy match ──────────────────────────────────────────────
    decision, score = fuzzy_match(
        user_answer, correct_answer,
        accept_threshold=fuzzy_accept,
        reject_threshold=fuzzy_reject,
    )
    logger.info("Eval fuzzy score=%d  %r vs %r", score, user_answer, correct_answer)

    if decision is True:
        logger.info("Eval fuzzy ✅  score=%d >= %d", score, fuzzy_accept)
        fb = await _generate_feedback(
            question, correct_answer, user_answer, True, language, lang_rules
        )
        return True, fb, f"fuzzy:{score}"

    if decision is False:
        logger.info("Eval fuzzy ❌  score=%d < %d", score, fuzzy_reject)
        fb = await _generate_feedback(
            question, correct_answer, user_answer, False, language, lang_rules
        )
        return False, fb, f"fuzzy_reject:{score}"

    # ── Stage 4: LLM semantic equivalence (uncertain zone) ───────────────
    logger.info("Eval LLM semantic (fuzzy=%d — uncertain zone %d–%d)",
                score, fuzzy_reject, fuzzy_accept)
    is_correct = await llm_semantic_check(question, correct_answer, user_answer)
    logger.info("Eval LLM semantic → %s", "✅" if is_correct else "❌")

    fb = await _generate_feedback(
        question, correct_answer, user_answer, is_correct, language, lang_rules
    )
    return is_correct, fb, f"llm_semantic:{score}"


def evaluate_mcq_answer(user_answer: str, correct_answer: str) -> bool:
    """
    MCQ evaluation — strict exact match only.
    MCQ options are displayed and clicked by the user; no semantic evaluation needed.
    """
    return user_answer.strip().lower() == correct_answer.strip().lower()
