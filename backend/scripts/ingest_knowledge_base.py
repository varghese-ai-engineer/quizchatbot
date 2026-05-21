"""
Knowledge Base Ingestion Script v3
====================================
Reads all .md files from knowledge_base/, auto-detects domain/topics/keywords,
stores metadata in MySQL knowledge_files, embeds chunks via Ollama, stores in ChromaDB.

Chunking Strategy (v3 — Markdown-Aware):
  - Splits on headings (##, ###) first so each section is its own semantic unit
  - Adds a breadcrumb prefix ("[File Section > Sub-section]") to each chunk so
    the embedding model captures full context, not just isolated text
  - Overlap-splits within sections only when a section exceeds MAX_CHUNK_CHARS
  - Falls back to paragraph-splitting for very long sections
  - Discards trivially short chunks (< MIN_CHUNK_LEN)

Usage:
    python scripts/ingest_knowledge_base.py           # incremental
    python scripts/ingest_knowledge_base.py --reset   # wipe ChromaDB & re-index all
    python scripts/ingest_knowledge_base.py --file ipl_knowledge_base.md  # single file
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import List

import httpx
import chromadb
import pymysql

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ingest")

# ── Config ────────────────────────────────────────────────────
OLLAMA_HOST     = os.getenv("OLLAMA_HOST",     "http://localhost:11434")
EMBED_MODEL     = os.getenv("EMBED_MODEL",     "nomic-embed-text")
CHROMA_HOST     = os.getenv("CHROMA_HOST",     "localhost")
CHROMA_PORT     = int(os.getenv("CHROMA_PORT", "8000"))
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "knowledge_base")
KNOWLEDGE_DIR   = os.path.join(os.path.dirname(__file__), "..", "knowledge_base")

MYSQL_HOST = os.getenv("DB_HOST", "mysql")
MYSQL_PORT = int(os.getenv("DB_PORT", "3306"))
MYSQL_USER = os.getenv("DB_USER", "quizchatbot")
MYSQL_PASS = os.getenv("DB_PASS", "quizchatbot")
MYSQL_DB   = os.getenv("DB_NAME", "quizchatbot")

# ── Chunking constants ────────────────────────────────────────
MAX_CHUNK_CHARS  = 400   # max characters per chunk
CHUNK_OVERLAP    = 75    # overlap chars when splitting long sections
MIN_CHUNK_LEN    = 40    # discard chunks shorter than this
SIMILARITY_THRESHOLD = 0.35   # kept here for reference — also set in rag_service.py

# ── Domain keyword map for auto-detection ─────────────────────
_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "cricket": ["ipl", "cricket", "wicket", "innings", "batting", "bowling", "odi",
                "t20", "test match", "century", "run", "over", "six", "sixes",
                "wicketkeeper", "captain", "team", "stadium"],
    "python":  ["python", "function", "class", "list", "dict", "loop", "variable",
                "import", "module"],
    "machine_learning": ["machine learning", "neural network", "model", "dataset",
                         "training", "accuracy", "regression", "classification"],
    "medical": ["medicine", "drug", "disease", "treatment", "symptom", "diagnosis",
                "patient", "dose"],
    "finance": ["stock", "market", "investment", "equity", "dividend", "portfolio",
                "trading"],
    "general": [],
}

# ── Per-domain default AI language rules ─────────────────────
_DEFAULT_RULES: dict[str, str] = {
    "cricket": (
        "Keep all player names in English exactly as written — do NOT transliterate.\n"
        "Keep all team names/abbreviations in English (CSK, MI, RCB, KKR etc.).\n"
        "Cricket terms may be used in the selected UI language where natural "
        "(e.g. சதம் for century in Tamil, शतक in Hindi).\n"
        "Keep numbers, dates, and statistics in their original form."
    ),
    "python": (
        "Keep all programming keywords, function names, class names, and API names in English.\n"
        "Keep code snippets exactly as written — do not translate code.\n"
        "Technical terms like list, dict, function, loop stay in English.\n"
        "Explanations should use the selected UI language naturally."
    ),
    "machine_learning": (
        "Keep all ML/AI terms in English (model, dataset, accuracy, loss, epoch, neural network).\n"
        "Keep library/framework names in English (TensorFlow, PyTorch, scikit-learn).\n"
        "Explanations should use the selected UI language naturally."
    ),
    "medical": (
        "Keep all medicine names, drug names, and medical terminology in English.\n"
        "Keep dosage values and measurements as-is.\n"
        "Explanations should use the selected UI language naturally."
    ),
    "general": (
        "Respond naturally in the selected UI language.\n"
        "Keep proper nouns and acronyms in their original form."
    ),
}


# ── Markdown-Aware Chunker ────────────────────────────────────

@dataclass
class Chunk:
    """A single text chunk with its metadata."""
    text: str            # the full text sent for embedding (includes breadcrumb)
    raw_text: str        # raw content without breadcrumb (for display)
    section: str         # section heading (e.g. "Batting Records")
    heading: str         # breadcrumb (e.g. "IPL Records > Batting Records")
    chunk_index: int     # sequential index across all chunks for this file


class MarkdownChunker:
    """
    Heading-aware markdown chunker.

    Strategy:
    1. Parse the document into (heading_path, content_block) pairs by splitting
       on H1/H2/H3 headings.
    2. For each content block:
       a. If short enough, emit as a single chunk.
       b. If too long, split on paragraph breaks first, then overlap-split remaining
          long paragraphs.
    3. Prepend a breadcrumb "[Parent > Section]" to each chunk so the embedding
       captures the section context even when text alone is ambiguous.
    """

    HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)

    def __init__(
        self,
        max_chars: int = MAX_CHUNK_CHARS,
        overlap: int = CHUNK_OVERLAP,
        min_len: int = MIN_CHUNK_LEN,
    ):
        self.max_chars = max_chars
        self.overlap   = overlap
        self.min_len   = min_len

    def chunk(self, text: str, filename: str = "") -> List[Chunk]:
        """Main entry point — returns ordered list of Chunk objects."""
        sections = self._split_into_sections(text)
        chunks: List[Chunk] = []
        idx = 0

        for heading_path, content in sections:
            breadcrumb = " > ".join(heading_path) if heading_path else filename
            for raw in self._split_content(content):
                raw = raw.strip()
                if len(raw) < self.min_len:
                    continue
                full_text = f"[{breadcrumb}]\n{raw}" if breadcrumb else raw
                chunks.append(Chunk(
                    text=full_text,
                    raw_text=raw,
                    section=heading_path[-1] if heading_path else "",
                    heading=breadcrumb,
                    chunk_index=idx,
                ))
                idx += 1

        return chunks

    # ── Private helpers ───────────────────────────────────────

    def _split_into_sections(self, text: str) -> list[tuple[list[str], str]]:
        """
        Split document into (heading_path, body_text) pairs.
        heading_path is a list of ancestor headings, e.g. ["IPL Records", "Batting Records"].
        """
        positions = [(m.start(), len(m.group(1)), m.group(2).strip())
                     for m in self.HEADING_RE.finditer(text)]

        if not positions:
            # No headings — treat whole document as one section
            return [([], text.strip())]

        sections: list[tuple[list[str], str]] = []
        # Content before the first heading
        preamble = text[:positions[0][0]].strip()
        if preamble and len(preamble) >= self.min_len:
            sections.append(([], preamble))

        # H1 stack
        h_stack: list[tuple[int, str]] = []  # (level, title)

        for i, (pos, level, title) in enumerate(positions):
            # Determine body text
            next_pos = positions[i + 1][0] if i + 1 < len(positions) else len(text)
            body = text[pos + len(f"{'#' * level} {title}"):next_pos].strip()

            # Maintain heading stack
            while h_stack and h_stack[-1][0] >= level:
                h_stack.pop()
            h_stack.append((level, title))

            heading_path = [t for _, t in h_stack]
            sections.append((heading_path, body))

        return sections

    def _split_content(self, content: str) -> list[str]:
        """
        Split a content block into chunks, respecting max_chars.
        First tries to split on blank-line paragraph boundaries.
        If a paragraph is still too long, falls back to overlap-based splitting.
        """
        if not content.strip():
            return []

        if len(content) <= self.max_chars:
            return [content]

        # Try paragraph splits (double newline)
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]
        if not paragraphs:
            return self._overlap_split(content)

        result: list[str] = []
        current = ""

        for para in paragraphs:
            # If adding this paragraph keeps us within limit, accumulate
            candidate = (current + "\n\n" + para).strip() if current else para
            if len(candidate) <= self.max_chars:
                current = candidate
            else:
                # Flush current
                if current:
                    result.append(current)
                # If the paragraph itself exceeds the limit, overlap-split it
                if len(para) > self.max_chars:
                    result.extend(self._overlap_split(para))
                    current = ""
                else:
                    current = para

        if current:
            result.append(current)

        return result if result else [content]

    def _overlap_split(self, text: str) -> list[str]:
        """
        Character-based overlap split as last resort for long paragraphs.
        This is the same algorithm as the old chunk_text() but used only
        when heading-aware and paragraph-based splitting isn't enough.
        """
        chunks, start = [], 0
        while start < len(text):
            end = min(start + self.max_chars, len(text))
            piece = text[start:end].strip()
            if len(piece) >= self.min_len:
                chunks.append(piece)
            start += self.max_chars - self.overlap
        return chunks


# ── Utilities ─────────────────────────────────────────────────

def get_embedding(text: str) -> list[float]:
    r = httpx.post(
        f"{OLLAMA_HOST}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["embedding"]


def make_id(source: str, idx: int, text: str) -> str:
    h = hashlib.md5(text.encode()).hexdigest()[:8]
    return f"{source}_{idx}_{h}"


def detect_domain(text: str, filename: str) -> str:
    combined = (filename + " " + text).lower()
    best, best_count = "general", 0
    for domain, kws in _DOMAIN_KEYWORDS.items():
        if domain == "general":
            continue
        count = sum(combined.count(kw) for kw in kws)
        if count > best_count:
            best, best_count = domain, count
    return best


def extract_topics(text: str) -> list[str]:
    """Extract H1/H2/H3 headings as topics."""
    headings = re.findall(r"^#{1,3}\s+(.+)$", text, re.MULTILINE)
    return [h.strip() for h in headings[:20]]


def extract_keywords(text: str, domain: str) -> list[str]:
    """Extract domain keywords that appear in the text."""
    kws = _DOMAIN_KEYWORDS.get(domain, [])
    found = [kw for kw in kws if kw in text.lower()]
    proper = re.findall(r"\b[A-Z][a-z]{2,}\b", text)
    combined = list(dict.fromkeys(found + proper))
    return combined[:30]


# ── MySQL helpers ─────────────────────────────────────────────

def get_mysql_conn():
    return pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT,
        user=MYSQL_USER, password=MYSQL_PASS,
        database=MYSQL_DB, charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def upsert_knowledge_file(conn, filename: str, domain: str, topics: list,
                           keywords: list, rules: str, chunk_count: int):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO knowledge_files
            (filename, domain_name, topics_json, keywords_json, ai_language_rules,
             chunk_count, indexed_at, status)
        VALUES (%s,%s,%s,%s,%s,%s,%s,'indexed')
        ON DUPLICATE KEY UPDATE
            domain_name=VALUES(domain_name),
            topics_json=VALUES(topics_json),
            keywords_json=VALUES(keywords_json),
            ai_language_rules=COALESCE(NULLIF(ai_language_rules,''), VALUES(ai_language_rules)),
            chunk_count=VALUES(chunk_count),
            indexed_at=VALUES(indexed_at),
            status='indexed'
    """, (filename, domain, json.dumps(topics), json.dumps(keywords),
          rules, chunk_count, datetime.utcnow()))
    conn.commit()
    cur.close()


def delete_knowledge_file_meta(conn, filename: str):
    cur = conn.cursor()
    cur.execute("DELETE FROM knowledge_files WHERE filename = %s", (filename,))
    conn.commit()
    cur.close()


# ── Main Ingestion ────────────────────────────────────────────

def ingest(target_file: str | None = None) -> None:
    reset_mode = "--reset" in sys.argv

    log.info("Connecting to ChromaDB at %s:%s ...", CHROMA_HOST, CHROMA_PORT)
    chroma = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

    if reset_mode:
        log.warning("--reset: deleting existing collection ...")
        try:
            chroma.delete_collection(name=COLLECTION_NAME)
        except Exception:
            pass

    collection = chroma.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})

    log.info("Connecting to MySQL ...")
    try:
        conn = get_mysql_conn()
        use_mysql = True
    except Exception as e:
        log.warning("MySQL unavailable (%s) — skipping metadata storage.", e)
        use_mysql = False
        conn = None

    kb_path  = os.path.abspath(KNOWLEDGE_DIR)
    all_mds  = sorted(f for f in os.listdir(kb_path) if f.endswith(".md"))
    md_files = [target_file] if target_file else all_mds

    if not md_files:
        log.error("No .md files found. Exiting.")
        sys.exit(0)

    # ── Remove stale chunks (files deleted from disk) ─────────
    if not reset_mode and not target_file:
        try:
            items = collection.get(include=["metadatas"])
            stale = [cid for cid, m in zip(items["ids"], items["metadatas"])
                     if m.get("source") not in all_mds]
            if stale:
                collection.delete(ids=stale)
                log.info("Removed %d stale chunks.", len(stale))
                if use_mysql:
                    removed = {m["source"] for m in items["metadatas"]
                               if m.get("source") not in all_mds}
                    for fn in removed:
                        delete_knowledge_file_meta(conn, fn)
        except Exception as e:
            log.warning("Stale cleanup error: %s", e)

    # ── Ingest each file ──────────────────────────────────────
    chunker = MarkdownChunker(
        max_chars=MAX_CHUNK_CHARS,
        overlap=CHUNK_OVERLAP,
        min_len=MIN_CHUNK_LEN,
    )

    for filename in md_files:
        filepath = os.path.join(kb_path, filename)
        if not os.path.exists(filepath):
            log.error("%s not found. Skipping.", filename)
            continue

        with open(filepath, encoding="utf-8") as fh:
            content = fh.read()

        chunks = chunker.chunk(content, filename=filename)
        domain = detect_domain(content, filename)
        topics = extract_topics(content)
        kws    = extract_keywords(content, domain)
        rules  = _DEFAULT_RULES.get(domain, _DEFAULT_RULES["general"])

        log.info("")
        log.info("📄 %s", filename)
        log.info("   Domain   : %s", domain)
        log.info("   Topics   : %s", topics[:5])
        log.info("   Chunks   : %d (was using naive splitter before)", len(chunks))

        # Log each chunk summary for visibility
        for i, chunk in enumerate(chunks):
            preview = chunk.raw_text[:80].replace("\n", " ")
            log.info("   Chunk[%02d] section=%-30s | %d chars | %r",
                     i, f'"{chunk.section}"', len(chunk.text), preview)

        # Remove old vectors for this file when re-indexing
        if target_file or reset_mode:
            try:
                old = collection.get(where={"source": filename})
                if old["ids"]:
                    collection.delete(ids=old["ids"])
                    log.info("   🗑️  Removed %d old chunks.", len(old["ids"]))
            except Exception:
                pass

        indexed = 0
        for chunk in chunks:
            cid = make_id(filename, chunk.chunk_index, chunk.text)
            existing = collection.get(ids=[cid])
            if existing["ids"]:
                log.info("   [%02d/%02d] skip (already indexed)", chunk.chunk_index + 1, len(chunks))
                continue
            emb = get_embedding(chunk.text)
            collection.add(
                ids=[cid],
                documents=[chunk.text],
                embeddings=[emb],
                metadatas=[{
                    "source":  filename,
                    "chunk":   chunk.chunk_index,
                    "domain":  domain,
                    "section": chunk.section,
                    "heading": chunk.heading,
                }],
            )
            indexed += 1
            log.info("   [%02d/%02d] ✓ indexed | section=%r",
                     chunk.chunk_index + 1, len(chunks), chunk.section)

        if use_mysql:
            upsert_knowledge_file(conn, filename, domain, topics, kws, rules, len(chunks))
            log.info("   ✅ Metadata saved to MySQL")

    if use_mysql and conn:
        conn.close()

    log.info("")
    log.info("✅ Ingestion complete.")


if __name__ == "__main__":
    target = None
    if "--file" in sys.argv:
        idx = sys.argv.index("--file")
        if idx + 1 < len(sys.argv):
            target = sys.argv[idx + 1]
    ingest(target_file=target)
