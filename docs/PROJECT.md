# QuizChatbot — Project Documentation

> A multilingual AI-powered training assistant combining Conversational RAG, Quiz Generation, Score Analytics, and real-time LLM streaming — all running locally with Docker and Ollama.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack](#2-tech-stack)
3. [Architecture](#3-architecture)
4. [What We Built](#4-what-we-built)
5. [Database Schema](#5-database-schema)
6. [API Reference](#6-api-reference)
7. [Test Coverage](#7-test-coverage)
8. [Known Constraints & Decisions](#8-known-constraints--decisions)
9. [Expansion Roadmap](#9-expansion-roadmap)

---

## 1. Project Overview

QuizChatbot is a self-hosted AI training assistant designed for organisations that want a **private, cost-free** alternative to GPT-based tools. It runs entirely on local hardware using Ollama (no API keys, no cloud dependency).

### Core Capabilities

| Capability | What it does |
|---|---|
| **RAG Chat** | Answers questions using uploaded `.md` knowledge files |
| **Quiz System** | Auto-generates trilingual MCQ + open-ended quizzes from knowledge files |
| **Score Analytics** | Natural language queries about quiz performance backed by MySQL |
| **SSE Streaming** | ChatGPT-style token-by-token response rendering |
| **Multilingual** | English, Tamil, Hindi — questions, answers, options, and feedback |
| **Admin Panel** | Upload knowledge, manage users, configure quiz settings |
| **Credit System** | 100 credits per user, 1 deducted per chat message |

---

## 2. Tech Stack

### Backend

| Component | Technology | Why |
|---|---|---|
| API Framework | **FastAPI** (Python 3.11) | Async-native, auto Swagger docs, `StreamingResponse` for SSE |
| ORM / DB Driver | **SQLAlchemy** + **PyMySQL** | Sync sessions for simplicity; PyMySQL required (mysql-connector unavailable in container) |
| Vector DB Client | **ChromaDB** 0.5.23 | Local-first, no cloud needed, cosine similarity search |
| LLM + Embeddings | **Ollama** (qwen2.5:7b + nomic-embed-text) | Fully local, no API cost, supports streaming |
| HTTP Client | **httpx** | Async streaming from Ollama API |
| Password Hashing | **passlib + bcrypt** | Industry standard |
| Validation | **Pydantic v2** | Schema validation on all API inputs |

### Frontend

| Component | Technology | Why |
|---|---|---|
| Server-side | **PHP 8.2** + Apache | Lightweight, session management, no build step |
| UI Framework | **Bootstrap 5.3** | Responsive grid, components |
| Markdown Render | **marked.js v9** | Client-side markdown → HTML for bot responses |
| Streaming | **Fetch API** + custom SSE parser | Typed `event:` fields, split-chunk safe |
| Icons | **Bootstrap Icons 1.11** | Consistent icon set |

### Infrastructure

| Component | Technology |
|---|---|
| Container Runtime | Docker + Docker Compose |
| Database | MySQL 8.0 (InnoDB, utf8mb4) |
| Vector Store | ChromaDB 0.5.23 |
| LLM Runtime | Ollama (host machine, port 11434) |
| PHP Server | Apache 2.4 (inside container) |

---

## 3. Architecture

### System Overview

```
┌─────────────────────────────────────────────────────┐
│                   User's Browser                    │
│         PHP Frontend (Apache — port 8090)           │
│    chat.php / quiz.php / admin/ / scores.php        │
└─────────────────┬───────────────────────────────────┘
                  │  POST /api/chat  (SSE streaming)
                  │  POST /api/quiz/*
                  │  POST /api/auth/*
                  ▼
┌─────────────────────────────────────────────────────┐
│              FastAPI Backend (port 8100)            │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │             Intent Router                    │  │
│  │  smalltalk │ rag │ sql │ quiz                │  │
│  └──────┬──────────┬──────────┬─────────────────┘  │
│         │          │          │                     │
│    ┌────▼────┐  ┌──▼──┐  ┌───▼──────────────────┐ │
│    │   RAG   │  │ SQL │  │    Quiz Generator    │ │
│    │ Service │  │Svc  │  │  (auto from .md)     │ │
│    └────┬────┘  └──┬──┘  └───┬──────────────────┘ │
│         │          │          │                     │
│    ┌────▼────┐  ┌──▼──┐  ┌───▼──────────────────┐ │
│    │ChromaDB │  │MySQL│  │   MySQL              │ │
│    │(vectors)│  │     │  │   quiz_questions      │ │
│    └────┬────┘  └─────┘  └──────────────────────┘ │
│         │                                           │
│    ┌────▼──────────────────────────┐               │
│    │   Ollama (host machine)       │               │
│    │   qwen2.5:7b + nomic-embed    │               │
│    └───────────────────────────────┘               │
└─────────────────────────────────────────────────────┘
```

### Knowledge File Upload Pipeline

```
Admin uploads .md file
        │
        ├──► Subprocess: ingest_knowledge_base.py
        │        ├── Markdown-aware chunking (heading breadcrumbs)
        │        ├── Ollama nomic-embed-text → vector per chunk
        │        ├── Store in ChromaDB collection
        │        └── Upsert metadata → knowledge_files (MySQL)
        │
        └──► Async task: quiz_generator.py
                 ├── LLM call: generate 3 open + 5 MCQ (English)
                 ├── LLM call: translate all to Tamil
                 ├── LLM call: translate all to Hindi
                 └── Insert → quiz_questions (9 language columns)
```

### SSE Chat Pipeline

```
User sends message
        │
        ▼
Intent Router (regex patterns)
        │
   ┌────┼────┬────────┐
   │    │    │        │
smalltalk  sql  quiz   rag
   │    │    │        │
  reply  MySQL  prompt  ChromaDB query
  (no   +LLM   hint    + LLM stream
  LLM)  stream
        │
        ▼
SSE frames: event:token / event:meta / event:done
        │
        ▼
Frontend: parseSSEStream() → blinking cursor → markdown render
```

---

## 4. What We Built

### 4.1 Backend Services

#### `services/intent_router.py`
- Classifies every message into: `smalltalk | rag | sql | quiz`
- Pure regex — no LLM call, sub-millisecond response
- Covers natural phrasings: "how i performed my recent test" → `sql`
- 34 regression tests

#### `services/rag_service.py`
- Embeds user query with `nomic-embed-text`
- Queries ChromaDB top-3 chunks with cosine similarity
- Similarity threshold `0.35` — rejects out-of-domain queries gracefully
- Structured debug logging per chunk (rank, similarity, source, section preview)
- Builds dynamic system prompt from global AI settings + per-file rules + language
- Streams tokens from Ollama one-by-one

#### `services/sql_service.py`
- Fetches last 5 completed quiz sessions from MySQL
- Formats data → LLM prompt → streams personalised performance summary
- Handles "no quizzes yet" gracefully in all 3 languages

#### `services/quiz_generator.py`
- Takes raw `.md` content as input
- Generates 3 open-ended + 5 MCQ questions via Ollama
- Robust JSON extraction: handles bare arrays, wrapped objects `{"questions": [...]}`
- All literal `{}` in prompt templates escaped as `{{}}` (str.format safety)
- Translates all questions, answers, options to Tamil and Hindi
- Stores all 9 language columns atomically

#### `services/ollama_service.py`
- `get_embedding()` — synchronous embedding via Ollama API
- `stream_llm()` — async generator yielding tokens from Ollama streaming API
- Handles `ReadTimeout` and `ConnectError` gracefully

#### `services/prompt_builder.py`
- Builds system prompt dynamically from:
  - Global AI instruction (from `global_ai_settings` table)
  - Per-file AI language rules (from `knowledge_files.ai_language_rules`)
  - Language-specific instruction block (EN / TA / HI)
  - Retrieved context chunks
  - Out-of-domain detection

### 4.2 API Routers

#### `routers/chat.py` — SSE Streaming
- `POST /api/chat` → `StreamingResponse(text/event-stream)`
- Typed SSE frames: `event:token`, `event:meta`, `event:done`
- `retry: 5000` — browser auto-reconnects on network drop
- Heartbeat comments every 3s
- Credit deduction + chat history saved after stream completes
- Admin-only: `debug_prompt` frame with full LLM context

#### `routers/quiz.py` — Quiz System
- Start quiz session, fetch question, submit answer
- LLM-evaluated open-ended answers with multilingual feedback
- Feedback sanitizer strips religious phrases, normalises "Correct / Wrong" prefix
- MCQ instant evaluation (no LLM needed)
- Quiz session completion with score, pass/fail, AI feedback summary

#### `routers/admin.py` — Admin Panel
- Upload `.md` files → triggers ingest subprocess + async quiz generation
- Delete files → removes from disk + ChromaDB + MySQL
- Reindex individual files
- List / download knowledge files
- User management (credits, activate/deactivate)
- Global AI settings (system instruction, prompt debug toggle)
- Quiz config (num questions, marks per Q, pass %)

#### `routers/auth.py` — Authentication
- Register (bcrypt password), Login (session token), Logout
- Role-based access: `user` / `admin`

### 4.3 Frontend Pages

| Page | File | Purpose |
|---|---|---|
| Landing | `index.php` | Redirects logged-in users to chat |
| Login | `login.php` | Auth form |
| Sign Up | `signup.php` | Registration form |
| Chat | `chat.php` + `chat.js` | SSE streaming chat interface |
| Quiz | `quiz.php` | Interactive quiz (MCQ + open) |
| Scores | `scores.php` | Quiz history and performance |
| Admin — Knowledge | `admin/knowledge.php` | Upload / delete `.md` files |
| Admin — Users | `admin/users.php` | User management |
| Admin — Quiz Config | `admin/quiz_config.php` | Global quiz settings |

### 4.4 Database

11 MySQL tables:

| Table | Purpose |
|---|---|
| `users` | Accounts, roles, credits, language preference |
| `sessions` | Auth session tokens |
| `chat_history` | Every message + intent + language |
| `credit_transactions` | Full audit trail of credit changes |
| `quiz_topics` | One topic per knowledge file |
| `quiz_questions` | Q&A with 9 language columns (EN/TA/HI) |
| `quiz_sessions` | Each quiz attempt with score |
| `quiz_answers` | Every submitted answer |
| `quiz_config` | Global quiz settings |
| `knowledge_files` | `.md` file metadata, status, AI rules |
| `global_ai_settings` | System instruction, prompt debug flag |

### 4.5 Scripts

| Script | Purpose |
|---|---|
| `scripts/ingest_knowledge_base.py` | Chunk `.md` → embed → ChromaDB + MySQL |
| `scripts/create_admin.py` | Interactive admin account creation |

---

## 5. Database Schema

### `quiz_questions` — Trilingual Design

```sql
question      TEXT  -- English
question_ta   TEXT  -- Tamil
question_hi   TEXT  -- Hindi
answer        TEXT  -- English
answer_ta     TEXT  -- Tamil
answer_hi     TEXT  -- Hindi
options       JSON  -- MCQ options (English)
options_ta    JSON  -- MCQ options (Tamil)
options_hi    JSON  -- MCQ options (Hindi)
type          ENUM('mcq','open')
difficulty    ENUM('easy','medium','hard')
```

The active language column is selected at quiz-serve time based on `users.language`.

### `knowledge_files` — Metadata Only

```sql
filename          VARCHAR(255)   -- physical file on disk
domain_name       VARCHAR(100)   -- e.g. 'cricket', 'general'
topics_json       JSON           -- extracted topics
keywords_json     JSON           -- extracted keywords
ai_language_rules TEXT           -- per-file prompt override
chunk_count       INT            -- number of ChromaDB chunks
status            ENUM('indexed','pending','error')
```

The raw content lives on disk at `/app/knowledge_base/`. MySQL stores only metadata.

---

## 6. API Reference

### Chat

```
POST /api/chat
Content-Type: application/json

{
  "message": "Who won the most IPL trophies?",
  "language": "en",          // en | ta | hi
  "user_id": 1
}

→ text/event-stream

event: token
data: {"token": "Mumbai "}

event: token
data: {"token": "Indians "}

event: meta
data: {"source": "teams.md", "credits": 99}

event: done
data: [DONE]
```

### Quiz

```
POST /api/quiz/start          → start session, get first question
POST /api/quiz/answer         → submit answer, get feedback + next question
POST /api/quiz/complete       → end session, get score + AI summary
GET  /api/quiz/sessions       → list user's quiz history
GET  /api/quiz/topics         → list available topics
```

### Admin

```
POST   /api/admin/knowledge/upload        → upload .md file
DELETE /api/admin/knowledge/{filename}    → delete file
POST   /api/admin/knowledge/reindex/{fn}  → re-index file
GET    /api/admin/knowledge               → list all files
GET    /api/admin/users                   → list users
PATCH  /api/admin/users/{id}/credits      → adjust credits
POST   /api/admin/settings                → update global AI instruction
```

---

## 7. Test Coverage

```
159 tests — 3 suites skipped (pre-existing stub issues)
```

| Suite | Tests | Covers |
|---|---|---|
| `test_intent_router.py` | 34 | Intent classification, natural phrasings, Tamil-English |
| `test_quiz_generator.py` | 15 | JSON extraction edge cases, prompt format safety |
| `test_chunker.py` | 20 | Markdown chunking, breadcrumbs, section isolation |
| `test_llm_feedback_sanitizer.py` | 6 | Trilingual feedback normalisation |
| `test_mcq_feedback.py` | 16 | MCQ correct/wrong strings for all languages |
| `test_sse_format.py` | 22 | SSE frame format, JSON encoding, unicode, frame ordering |
| `test_prompt_debug.py` | 4 | Prompt debug flag behaviour |
| `test_auth.py` | 3 | Auth endpoints (1 pre-existing bcrypt stub failure) |
| `test_schemas.py` | 3 | Pydantic schema validation (2 stub failures) |

---

## 8. Known Constraints & Decisions

| Decision | Reason |
|---|---|
| **PyMySQL only** (not mysql-connector-python) | mysql-connector-python not present in container; PyMySQL is the only available driver |
| **Physical `.md` files** (not MySQL BLOB) | Ingest subprocess reads directly from disk; reindex works anytime without re-upload |
| **Ollama on host** (not inside Docker) | GPU/CPU model serving requires access to host hardware; Docker can't easily share GPU |
| **Sync SQLAlchemy** (not async) | Simpler session management for the current request volume; async SQLAlchemy adds complexity without benefit at this scale |
| **Regex intent router** (not LLM-based) | Sub-ms classification, no credit cost, no LLM dependency for routing |
| **Similarity threshold 0.35** | Raised from 0.30 to reduce retrieval of weakly-related chunks while keeping relevant results |

---

## 9. Expansion Roadmap

### 🟢 Short-Term (Next Sprint)

| Feature | Details |
|---|---|
| **Conversation memory** | Pass last 3–5 chat turns as context in RAG prompt so responses are coherent in follow-up questions |
| **User feedback** | 👍 / 👎 buttons on each bot response; store in `chat_feedback` table for model evaluation |
| **Response caching** | Cache RAG answers for identical queries (Redis or in-memory LRU) — 80% of questions repeat |
| **Quiz retry mode** | Let users retake only the questions they got wrong |
| **PDF upload support** | Extract text from PDF and convert to `.md` before ingest |

### 🟡 Medium-Term

| Feature | Details |
|---|---|
| **Leaderboard** | Public ranking of quiz scores per topic |
| **Admin analytics dashboard** | Credit usage graphs, popular questions, per-user engagement, intent distribution |
| **LLM model selector** | Admin can switch between `qwen2.5:7b`, `llama3`, `mistral` from the UI without restarting |
| **Role: Teacher** | Teachers can create custom question sets, assign to groups of users |
| **Progressive difficulty** | Quiz adapts difficulty based on user's recent performance |
| **WhatsApp / Telegram bot** | Expose the same chat API through a messaging platform for wider reach |
| **JWT auth** | Replace simple session tokens with JWT + refresh token rotation |

### 🔴 Long-Term / Architectural

| Feature | Details |
|---|---|
| **Multi-tenancy** | Organisation-level isolation — each org has its own knowledge base, users, and settings |
| **Cloud-optional deployment** | Deploy to a VPS (DigitalOcean/Hetzner) with Ollama on the server, or swap Ollama for OpenAI/Gemini API |
| **Hybrid search** | Combine ChromaDB semantic search with MySQL full-text keyword search for higher recall |
| **Fine-tuning pipeline** | Collect user feedback → curate good Q&A pairs → fine-tune the LLM on domain-specific data |
| **Mobile app** | React Native / Flutter app consuming the same FastAPI endpoints |
| **WebSocket upgrade** | Replace SSE with WebSocket for true bidirectional conversation (typing indicators, reactions) |
| **Auto knowledge refresh** | Watch a folder / Google Drive for new `.md` files and auto-ingest on change |
| **Certificate system** | Issue completion certificates (PDF) when a user achieves a score threshold on a topic |

---

## Project Stats

| Metric | Count |
|---|---|
| Backend Python files | 18 |
| Frontend PHP/JS/CSS files | 14 |
| Database tables | 11 |
| API endpoints | ~25 |
| Test cases | 159 |
| Languages supported | 3 (EN / TA / HI) |
| `.md` knowledge files | 12 |
| Docker containers | 4 |
