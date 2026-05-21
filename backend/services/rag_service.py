"""
RAG Service — semantic search in ChromaDB + dynamic prompt building + LLM streaming.

Retrieval strategy (v2):
  - Embeds the query via Ollama nomic-embed-text
  - Queries ChromaDB for top_k semantically closest chunks
  - Uses cosine similarity threshold of 0.35 (raised from 0.30) to reject noise
  - Logs every retrieved chunk with its score, source file, section, and chunk ID
    so developers can diagnose exactly why a chunk was or wasn't returned
"""
from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy.orm import Session

from db.chroma import get_collection
from services.ollama_service import get_embedding, stream_llm
from services.prompt_builder import build_system_prompt, get_out_of_domain_reply

logger = logging.getLogger(__name__)

# Cosine similarity threshold — below this = out-of-domain
# Raised from 0.30 → 0.35 to reduce retrieval of weakly-related chunks
SIMILARITY_THRESHOLD = 0.35


async def rag_stream(
    query: str,
    language: str = "en",
    top_k: int = 3,
    db: Optional[Session] = None,
) -> AsyncGenerator[dict, None]:
    """
    1. Embed the query
    2. Search ChromaDB for top_k relevant chunks (with distances)
    3. Log all retrieved chunks with scores for debugging
    4. Detect out-of-domain via similarity score
    5. Build dynamic system prompt from global + per-file rules + language
    6. Stream LLM answer token by token

    Yields dicts: {"token": str} | {"source": str} | {"debug_prompt": str} | {"done": True}
    """
    # ── Step 1: Embed ─────────────────────────────────────────
    query_embedding = await get_embedding(query)

    # ── Step 2: Retrieve from ChromaDB ───────────────────────
    collection = get_collection()

    # Get collection count safely
    try:
        count = collection.count()
    except Exception:
        count = 0

    if count == 0:
        logger.warning("RAG: ChromaDB collection is empty — no chunks indexed yet.")
        yield {"token": get_out_of_domain_reply(language)}
        yield {"done": True}
        return

    actual_k = min(top_k, count)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=actual_k,
        include=["documents", "metadatas", "distances"],
    )

    docs      = results.get("documents",  [[]])[0]
    metas     = results.get("metadatas",  [[]])[0]
    distances = results.get("distances",  [[]])[0]
    ids       = results.get("ids",        [[]])[0]

    # ── Step 3: Structured retrieval debug logging ────────────
    logger.info(
        "RAG RETRIEVAL — query=%r | top_k=%d | collection_size=%d",
        query[:80], actual_k, count,
    )
    for rank, (doc_id, meta, dist, doc) in enumerate(
        zip(ids, metas, distances, docs), start=1
    ):
        similarity = 1.0 - (dist / 2.0)
        source  = meta.get("source",  "unknown")
        section = meta.get("section", "")
        heading = meta.get("heading", "")
        preview = doc[:100].replace("\n", " ") if doc else ""
        logger.info(
            "  [%d] id=%-35s | similarity=%.4f | source=%-25s | section=%r",
            rank, doc_id, similarity, source, section,
        )
        logger.info(
            "       heading=%-45s | preview: %r",
            heading, preview,
        )

    # ── Step 4: Confidence / out-of-domain check ─────────────
    # ChromaDB cosine space: distance ∈ [0, 2], similarity = 1 - distance/2
    best_distance   = distances[0] if distances else 2.0
    best_similarity = 1.0 - (best_distance / 2.0)

    logger.info(
        "RAG best_similarity=%.4f | threshold=%.2f | %s",
        best_similarity,
        SIMILARITY_THRESHOLD,
        "✓ IN-DOMAIN" if best_similarity >= SIMILARITY_THRESHOLD else "✗ OUT-OF-DOMAIN",
    )

    if not docs or best_similarity < SIMILARITY_THRESHOLD:
        logger.info(
            "RAG: rejecting query — best_similarity=%.4f < threshold=%.2f",
            best_similarity, SIMILARITY_THRESHOLD,
        )
        yield {"token": get_out_of_domain_reply(language)}
        yield {"done": True}
        return

    # ── Step 5: Build dynamic prompt ─────────────────────────
    context      = "\n\n---\n\n".join(docs)
    source_files = list({m.get("source", "") for m in metas if m.get("source")})
    source_file  = metas[0].get("source", "") if metas else ""

    system_prompt, is_ood = build_system_prompt(
        context=context,
        source_files=source_files,
        language=language,
        db=db,
        similarity_score=best_similarity,
    )

    if is_ood:
        yield {"token": system_prompt}   # system_prompt contains the polite rejection
        yield {"done": True}
        return

    # ── Step 6: Stream LLM ───────────────────────────────────
    # Build the debug_prompt payload — includes retrieved chunk details for admin
    retrieved_summary = "\n".join(
        f"  [{i+1}] {meta.get('source','?')} > {meta.get('section','?')} "
        f"(similarity={1.0 - (dist / 2.0):.4f})"
        for i, (meta, dist) in enumerate(zip(metas, distances))
    )
    debug_text = (
        f"=== RETRIEVED CHUNKS ===\n{retrieved_summary}\n\n"
        f"=== SYSTEM PROMPT ===\n{system_prompt}\n\n"
        f"=== USER QUERY ===\n{query}"
    )
    yield {"debug_prompt": debug_text}

    async for token in stream_llm(system_prompt, query):
        yield {"token": token}

    if source_file:
        yield {"source": source_file}

    yield {"done": True}
