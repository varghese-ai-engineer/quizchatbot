# QuizChatbot 🤖

**Multilingual AI-Powered Training Assistant**

A full-stack AI learning system combining Conversational AI, RAG, Quiz Platform, and Multilingual support.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | PHP 8.2 + Bootstrap 5 + JavaScript |
| Backend | FastAPI (Python 3.11) |
| Database | MySQL 8.0 |
| Vector DB | ChromaDB 0.5.x |
| LLM | Ollama + Llama3 8B |
| Embeddings | nomic-embed-text |
| Streaming | SSE (Server-Sent Events) |
| Container | Docker + Docker Compose |

---

## Architecture

```
Browser
   ↓
PHP + Bootstrap UI
   ↓ AJAX / SSE
FastAPI Backend
   ↓
Intent Router
 ┌──────────┬──────────┐
 │          │          │
RAG        SQL       Quiz
 │          │          │
ChromaDB  MySQL     MySQL
 │
Ollama + Llama3
```

---

## Quick Start

### Prerequisites
- Docker Desktop
- Ollama running locally with Llama3 and nomic-embed-text pulled

```bash
# Pull required Ollama models
ollama pull llama3
ollama pull nomic-embed-text
```

### 1. Clone and configure

```bash
git clone <repo-url>
cd quizchatbot

cp .env.example .env
# Edit .env if needed
```

### 2. Start all services

```bash
docker compose up --build -d
```

Services will be available at:
- **Frontend (PHP)** → http://localhost:8080
- **FastAPI API** → http://localhost:8000
- **API Docs** → http://localhost:8000/docs
- **ChromaDB** → http://localhost:8001
- **MySQL** → localhost:3307

### 3. Ingest Knowledge Base

After containers are running:

```bash
docker compose exec api python scripts/ingest_knowledge_base.py
```

### 4. Open the app

Visit → **http://localhost:8080**

Register an account → login → start chatting!

---

## Running Tests

```bash
cd backend
pip install pytest httpx
pytest -v
```

### Test Suites
| File | What it tests |
|------|--------------|
| `tests/test_intent_router.py` | Intent classification (18 cases) |
| `tests/test_auth.py` | Auth register/login endpoints |
| `tests/test_schemas.py` | Pydantic schema validation |

---

## Project Structure

```
quizchatbot/
├── backend/
│   ├── main.py                   # FastAPI app
│   ├── config.py                 # Settings (env-driven)
│   ├── db/
│   │   ├── mysql.py              # MySQL connection
│   │   └── chroma.py             # ChromaDB client
│   ├── models/
│   │   └── schemas.py            # Pydantic schemas
│   ├── routers/
│   │   ├── auth.py               # /api/auth/*
│   │   ├── chat.py               # /api/chat (SSE)
│   │   └── quiz.py               # /api/quiz/*
│   ├── services/
│   │   ├── ollama_service.py     # Embeddings + LLM streaming
│   │   ├── intent_router.py      # Message → intent
│   │   ├── rag_service.py        # RAG pipeline
│   │   └── sql_service.py        # Score query + LLM
│   ├── scripts/
│   │   └── ingest_knowledge_base.py
│   └── tests/
│       ├── test_intent_router.py
│       ├── test_auth.py
│       └── test_schemas.py
├── frontend/
│   ├── config/config.php
│   ├── src/
│   │   ├── Auth.php
│   │   └── Database.php
│   └── public/
│       ├── index.php
│       ├── login.php
│       ├── signup.php
│       ├── chat.php
│       ├── logout.php
│       └── assets/
│           ├── css/auth.css
│           ├── css/chat.css
│           ├── js/auth.js
│           └── js/chat.js
├── database/
│   ├── schema.sql
│   └── seed.sql
├── knowledge_base/
│   ├── python_basics.md
│   ├── machine_learning.md
│   └── data_structures.md
├── docker-compose.yml
├── .env.example
└── .gitignore
```

---

## Features

- 💬 **Conversational AI** — RAG-powered answers from markdown knowledge base
- 📊 **Score Queries** — "How did I do in my last quiz?" → MySQL + LLM response
- 🎯 **Quiz System** — Topic-based quizzes with AI feedback
- 🌐 **Multilingual** — English, Tamil, Hindi support
- ⚡ **SSE Streaming** — ChatGPT-style token-by-token responses
- 💳 **Credit System** — 100 credits per user, 1 per message
- 📎 **Source Citation** — Shows which markdown file answered the question
- 🐳 **Dockerized** — Full stack runs in one `docker compose up`

---

## Roadmap

- [ ] JWT authentication (replace simple token)
- [ ] Admin dashboard (credit usage, quiz analytics)
- [ ] Response caching for repeated questions
- [ ] User feedback (👍 / 👎) for model improvement
- [ ] More knowledge base articles
