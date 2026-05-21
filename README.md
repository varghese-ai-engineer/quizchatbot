# QuizChatbot 🤖

**Multilingual AI-Powered Training Assistant**

A full-stack, self-hosted AI learning system combining Conversational RAG, Auto-generated Quizzes, Score Analytics, and real-time LLM streaming — running entirely on local hardware with Docker + Ollama.

---

## 📚 Documentation

| Doc | Description |
|---|---|
| [**SETUP.md**](docs/SETUP.md) | Step-by-step guide to run on any new device |
| [**PROJECT.md**](docs/PROJECT.md) | Architecture, tech stack, what we built, and roadmap |

---

## Quick Start

```bash
# 1. Pull Ollama models (one-time)
ollama pull qwen2.5:7b
ollama pull nomic-embed-text

# 2. Clone and start
git clone https://github.com/varghese-ai-engineer/quizchatbot.git
cd quizchatbot
docker compose up --build -d

# 3. Index knowledge base
docker compose exec api python scripts/ingest_knowledge_base.py

# 4. Open → http://localhost:8090
```

See **[SETUP.md](docs/SETUP.md)** for full instructions, troubleshooting, and Windows notes.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | PHP 8.2 + Bootstrap 5.3 + Vanilla JS |
| Backend | FastAPI (Python 3.11) |
| Database | MySQL 8.0 |
| Vector DB | ChromaDB 0.5.23 |
| LLM | Ollama + qwen2.5:7b |
| Embeddings | nomic-embed-text |
| Streaming | SSE (Server-Sent Events) — typed event fields |
| Containers | Docker + Docker Compose |

---

## Features

- 💬 **Conversational RAG** — answers from uploaded `.md` knowledge files
- 🎯 **Auto-generated Quizzes** — MCQ + open-ended from any knowledge file
- 🌐 **Trilingual** — English, Tamil, Hindi (questions, answers, options, feedback)
- ⚡ **SSE Streaming** — ChatGPT-style token-by-token rendering with stop button
- 📊 **Score Analytics** — "how i performed my recent test" → MySQL + LLM
- 🔐 **Admin Panel** — upload knowledge, manage users, configure quiz settings
- 💳 **Credit System** — 100 credits per user, 1 per chat message
- 🐳 **Fully Dockerized** — 4 containers, one command startup

---

## Service Ports

| Service | Port | URL |
|---|---|---|
| Frontend (PHP) | 8090 | http://localhost:8090 |
| FastAPI backend | 8100 | http://localhost:8100/docs |
| ChromaDB | 8200 | http://localhost:8200 |
| MySQL | 3307 | localhost:3307 |

---

## Tests

```bash
docker compose exec api pytest tests/ -v
# 159 tests
```

---

## Project Structure

```
quizchatbot/
├── docs/
│   ├── SETUP.md              ← Setup guide for new devices
│   └── PROJECT.md            ← Full architecture & roadmap
├── backend/
│   ├── routers/              ← chat, quiz, admin, auth
│   ├── services/             ← rag, sql, quiz_generator, intent_router
│   ├── db/                   ← mysql, chroma clients
│   ├── scripts/              ← ingest, create_admin
│   └── tests/                ← 159 tests across 9 suites
├── frontend/
│   └── public/               ← chat, quiz, scores, admin pages
├── database/
│   ├── schema.sql            ← 11 tables, utf8mb4
│   └── seed.sql
├── knowledge_base/           ← .md source files
└── docker-compose.yml
```
