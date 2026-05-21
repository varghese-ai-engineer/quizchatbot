"""
SQL Service — query MySQL for user scores, then generate LLM response.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.orm import Session

from db.mysql import fetch_all, fetch_one  # noqa: F401
from services.ollama_service import stream_llm
from services.prompt_builder import _LANGUAGE_BASE

SQL_SYSTEM_PROMPT = """You are a friendly AI tutor.
Based on the quiz performance data below, give the user an encouraging,
personalized summary of their progress.

{language_instructions}

Rules:
- Do NOT include any religious phrases, blessings, or emotional filler.
- Keep technical terms (quiz, score, topic, percentage) in English.

Data:
{data}
"""


async def sql_stream(
    user_id: int,
    query: str,
    language: str,
    db: Session,
) -> AsyncGenerator[dict, None]:
    """
    Fetch score data from MySQL and stream an LLM response.
    """
    # Fetch last 5 quiz sessions
    rows = fetch_all(
        db,
        """
        SELECT qs.id, qt.name AS topic, qs.score, qs.total_questions,
               qs.started_at, qs.ended_at
        FROM   quiz_sessions qs
        JOIN   quiz_topics   qt ON qt.id = qs.topic_id
        WHERE  qs.user_id = :uid AND qs.completed = 1
        ORDER  BY qs.started_at DESC
        LIMIT  5
        """,
        {"uid": user_id},
    )

    if not rows:
        no_data = {
            "en": "You haven't completed any quizzes yet. Start one now!",
            "ta": "நீங்கள் இன்னும் எந்த quiz-உம் complete பண்ணவில்லை. ஒன்று start பண்ணுங்க!",
            "hi": "आपने अभी तक कोई quiz पूरा नहीं किया है। अभी एक शुरू करें!",
        }
        yield {"token": no_data.get(language, no_data["en"])}
        yield {"done": True}
        return

    data_text = "\n".join(
        f"- {r['topic']}: {r['score']}/{r['total_questions']} "
        f"on {str(r['started_at'])[:10]}"
        for r in rows
    )

    lang_instructions = _LANGUAGE_BASE.get(language, _LANGUAGE_BASE["en"])
    system_prompt = SQL_SYSTEM_PROMPT.format(
        language_instructions=lang_instructions,
        data=data_text,
    )

    async for token in stream_llm(system_prompt, query):
        yield {"token": token}

    yield {"done": True}
