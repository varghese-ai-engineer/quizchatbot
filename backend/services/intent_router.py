"""
Intent Router — classifies user message into: smalltalk | sql | quiz | rag
"""
from __future__ import annotations
import re

# ── Smalltalk / greetings (handled without LLM or RAG) ───────
_SMALLTALK_PATTERNS = [
    r"^\s*(hi|hello|hey|hiya|howdy)\s*[!.]?\s*$",
    r"^\s*good\s*(morning|afternoon|evening|night)\s*[!.]?\s*$",
    r"^\s*thank\s*(you|u|s)\b",
    r"^\s*thanks\b",
    r"^\s*(bye|goodbye|see\s*you|cya)\s*[!.]?\s*$",
    r"^\s*(how are you|how r u|whats up|what's up)\s*[!.]?\s*$",
    r"^\s*(ok|okay|cool|great|nice|good|got it|got\s*it|alright)\s*[!.]?\s*$",
    r"^\s*(yes|no|yeah|nope|sure|ok)\s*[!.]?\s*$",
]

_SMALLTALK_REPLIES = {
    "en": "Hey! 👋 I'm your AI assistant. Ask me anything about the knowledge base, or start a quiz!",
    "ta": "வணக்கம்! 👋 நான் உங்கள் AI assistant. Knowledge base பத்தி கேளுங்க, அல்லது quiz start பண்ணுங்க!",
    "hi": "नमस्ते! 👋 मैं आपका AI assistant हूं। Knowledge base के बारे में पूछें, या quiz शुरू करें!",
}

_THANKS_REPLIES = {
    "en": "You're welcome! 😊 Is there anything else I can help you with?",
    "ta": "சரிதான்! 😊 இன்னும் ஏதாவது கேக்கணுமா?",
    "hi": "कोई बात नहीं! 😊 क्या और कुछ पूछना है?",
}

_BYE_REPLIES = {
    "en": "Goodbye! 👋 Come back anytime to learn more.",
    "ta": "சரி, போய் வாங்க! 👋 மீண்டும் வாங்க.",
    "hi": "अलविदा! 👋 दोबारा आएं।",
}

# ── SQL / Score intent ────────────────────────────────────────
_SQL_PATTERNS = [
    # Explicit score/result words
    r"\bscore\b",
    r"\bresult\b",
    r"\bmarks?\b",
    r"\brank\b",
    # Performance queries
    r"\bhow did i\b",
    r"\bhow i did\b",
    r"\bhow i perform",          # "how i performed", "how i perform"
    r"\bi perform",              # "how did i perform"
    r"\bmy performance\b",
    r"\bmy progress\b",
    r"\bmy stats?\b",
    # Test/quiz history references
    r"\blast quiz\b",
    r"\blast test\b",
    r"\brecent quiz\b",
    r"\brecent test\b",
    r"\bmy quiz\b",
    r"\bmy test\b",
    r"\bquiz history\b",
    r"\btest history\b",
    # Pass/fail queries
    r"\bdid i pass\b",
    r"\bdid i fail\b",
    # Credits
    r"\bcredits?\b",
]

# ── Quiz intent ───────────────────────────────────────────────
_QUIZ_PATTERNS = [
    r"\bquiz\s*me\b", r"\btest\s*my\b", r"\bexam\b",
    r"\bpractice\b", r"start a quiz", r"quiz on",
    r"\bquiz\b.*\bon\b",
]


def detect_intent(message: str) -> str:
    """
    Returns one of: 'smalltalk' | 'sql' | 'quiz' | 'rag'
    """
    msg = message.lower().strip()

    for pattern in _SMALLTALK_PATTERNS:
        if re.search(pattern, msg, re.IGNORECASE):
            return "smalltalk"

    for pattern in _SQL_PATTERNS:
        if re.search(pattern, msg):
            return "sql"

    for pattern in _QUIZ_PATTERNS:
        if re.search(pattern, msg):
            return "quiz"

    return "rag"


def get_smalltalk_reply(message: str, language: str = "en") -> str:
    """Return a canned smalltalk response without calling the LLM."""
    msg = message.lower().strip()
    lang = language if language in ("en", "ta", "hi") else "en"

    if re.search(r"\bthank", msg):
        return _THANKS_REPLIES[lang]
    if re.search(r"\b(bye|goodbye|see you|cya)\b", msg):
        return _BYE_REPLIES[lang]
    return _SMALLTALK_REPLIES[lang]
