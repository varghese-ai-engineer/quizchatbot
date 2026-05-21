"""
Prompt Builder — dynamically assembles the final LLM system prompt from:
  1. Global special instructions (from MySQL global_ai_settings)
  2. Per-file AI language rules (from MySQL knowledge_files, matched by source)
  3. Selected UI language instructions
  4. Retrieved context

Flow:
  Global Instructions
  + Matched File AI Rules (merged, deduplicated)
  + Language Instructions
  + Context
  → Final System Prompt
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session
from db.mysql import fetch_all, fetch_one

logger = logging.getLogger(__name__)

# ── Base language instructions ────────────────────────────────
# IMPORTANT: These prompts are very explicit and example-driven because
# local LLMs (qwen2.5, llama3) often try to transliterate English words
# into Tamil/Hindi script, producing garbage. The examples show the model
# exactly what correct output looks like.
_LANGUAGE_BASE: dict[str, str] = {
    "en": "Respond in clear, simple, conversational English.",
    "ta": (
        "IMPORTANT: Respond in SIMPLE, SPOKEN Tamil (தமிழ்) mixed with English words.\n"
        "\n"
        "STRICT RULES:\n"
        "1. Keep ALL player names in ENGLISH script: Chris Gayle, Virat Kohli, MS Dhoni (NEVER transliterate into Tamil script)\n"
        "2. Keep ALL team names in ENGLISH: CSK, MI, RCB, KKR (NEVER write in Tamil script)\n"
        "3. Keep ALL numbers and stats in ENGLISH: 358, 175*, 6/12 (NEVER convert to Tamil numerals)\n"
        "4. Use simple spoken Tamil for connecting words and explanations\n"
        "5. Do NOT use formal or literary Tamil\n"
        "6. Do NOT include religious phrases, blessings, or emotional filler\n"
        "7. Do NOT transliterate English words into Tamil script — keep them in English\n"
        "\n"
        "CORRECT example:\n"
        "IPL-ல் அதிகமான sixes அடிச்சது Chris Gayle தான். அவர் 358+ sixes அடிச்சிருக்காரு. "
        "RCB-க்காக 2013-ல் 175* runs எடுத்தப்ப ஒரே innings-ல் 17 sixes அடிச்சாரு.\n"
        "\n"
        "WRONG example (DO NOT DO THIS):\n"
        "சிரிஸ் கெய்ல் ஐ.பி.எல்-ல் ௩௫௮ சிக்ஸர்கள் அடித்துள்ளார்.\n"
        "\n"
        "The CORRECT example above is exactly how you must write. Mix English words naturally into Tamil sentences."
    ),
    "hi": (
        "IMPORTANT: Respond in SIMPLE, SPOKEN Hindi mixed with English words.\n"
        "\n"
        "STRICT RULES:\n"
        "1. Keep ALL player names in ENGLISH script: Chris Gayle, Virat Kohli, MS Dhoni (NEVER transliterate into Hindi/Devanagari)\n"
        "2. Keep ALL team names in ENGLISH: CSK, MI, RCB, KKR (NEVER write in Hindi script)\n"
        "3. Keep ALL numbers and stats in ENGLISH: 358, 175*, 6/12\n"
        "4. Use simple spoken Hindi for connecting words and explanations\n"
        "5. Do NOT use formal or literary Hindi\n"
        "6. Do NOT include religious phrases, blessings, or emotional filler\n"
        "7. Do NOT transliterate English words into Hindi script — keep them in English\n"
        "\n"
        "CORRECT example:\n"
        "IPL में सबसे ज्यादा sixes Chris Gayle ने मारे हैं। उन्होंने 358+ sixes मारे हैं। "
        "2013 में RCB के लिए 175* runs बनाते हुए एक ही innings में 17 sixes मारे थे।\n"
        "\n"
        "WRONG example (DO NOT DO THIS):\n"
        "क्रिस गेल ने आई.पी.एल. में ३५८ छक्के लगाए हैं।\n"
        "\n"
        "The CORRECT example above is exactly how you must write. Mix English words naturally into Hindi sentences."
    ),
}

_PROMPT_TEMPLATE = """\
=== GLOBAL INSTRUCTIONS ===
{global_instructions}

=== LANGUAGE INSTRUCTIONS ===
{language_instructions}

=== DOMAIN-SPECIFIC AI RULES ===
{domain_rules}

=== KNOWLEDGE BASE CONTEXT ===
{context}

Answer the user's question based ONLY on the context above.
If the context does not contain enough information to answer confidently, say so honestly and politely.
Do NOT hallucinate or invent facts not present in the context.

CRITICAL: You MUST follow the LANGUAGE INSTRUCTIONS above exactly. Keep all names, numbers, and team names in English script. Do NOT transliterate them.
"""

_OUT_OF_DOMAIN = {
    "en": (
        "I'm sorry, I couldn't find relevant information about that in the current knowledge base. "
        "Please ask something related to the available topics."
    ),
    "ta": (
        "மன்னிக்கவும், இந்த கேள்விக்கு தொடர்புடைய தகவல்கள் knowledge base-ல் இல்லை. "
        "கிடைக்கக்கூடிய தலைப்புகள் பத்தி கேளுங்க."
    ),
    "hi": (
        "क्षमा करें, मुझे इस प्रश्न से संबंधित जानकारी knowledge base में नहीं मिली। "
        "कृपया उपलब्ध विषयों से संबंधित कुछ पूछें।"
    ),
}


def get_out_of_domain_reply(language: str = "en") -> str:
    return _OUT_OF_DOMAIN.get(language, _OUT_OF_DOMAIN["en"])


def build_system_prompt(
    context: str,
    source_files: list[str],
    language: str,
    db: Optional[Session] = None,
    similarity_score: float = 1.0,
) -> tuple[str, bool]:
    """
    Build the final LLM system prompt.

    Returns:
        (system_prompt, is_out_of_domain)

    Args:
        context:          Retrieved text chunks joined as string
        source_files:     List of source .md filenames that matched
        language:         UI language code ('en', 'ta', 'hi')
        db:               SQLAlchemy session for MySQL lookups
        similarity_score: Cosine similarity of best match (0-1).
                          Below threshold → out-of-domain
    """
    # ── Out-of-domain detection ───────────────────────────────
    SIMILARITY_THRESHOLD = 0.35   # cosine distance threshold
    if similarity_score < SIMILARITY_THRESHOLD or not context.strip():
        return get_out_of_domain_reply(language), True

    # ── 1. Global special instructions ───────────────────────
    global_instructions = _get_global_instructions(db)

    # ── 2. Language base instructions ────────────────────────
    lang_instructions = _LANGUAGE_BASE.get(language, _LANGUAGE_BASE["en"])

    # ── 3. Per-file domain AI rules ──────────────────────────
    domain_rules = _get_merged_file_rules(source_files, db)

    prompt = _PROMPT_TEMPLATE.format(
        global_instructions=global_instructions,
        language_instructions=lang_instructions,
        domain_rules=domain_rules or "No specific domain rules.",
        context=context,
    )
    return prompt, False


# ── Helpers ───────────────────────────────────────────────────

def _get_global_instructions(db: Optional[Session]) -> str:
    """Fetch all active global instructions from MySQL."""
    if db is None:
        return "Be helpful, honest, and concise."
    try:
        rows = fetch_all(
            db,
            "SELECT global_special_instruction FROM global_ai_settings WHERE is_active = 1",
            {},
        )
        if rows:
            return "\n".join(r["global_special_instruction"] for r in rows)
    except Exception as e:
        logger.warning("Could not fetch global instructions: %s", e)
    return "Be helpful, honest, and concise."


def _get_merged_file_rules(source_files: list[str], db: Optional[Session]) -> str:
    """
    Fetch per-file AI language rules for each matched source file,
    merge them, deduplicate, and return as a single instruction block.
    """
    if not source_files or db is None:
        return ""

    rules: list[str] = []
    seen: set[str] = set()

    for filename in source_files:
        try:
            row = fetch_one(
                db,
                "SELECT ai_language_rules, domain_name FROM knowledge_files WHERE filename = :fn",
                {"fn": filename},
            )
            if row and row["ai_language_rules"]:
                for line in row["ai_language_rules"].splitlines():
                    line = line.strip()
                    if line and line not in seen:
                        seen.add(line)
                        rules.append(line)
        except Exception as e:
            logger.warning("Could not fetch rules for %s: %s", filename, e)

    return "\n".join(rules) if rules else ""
