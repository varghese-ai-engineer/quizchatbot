# 🚀 QuizChatbot — Setup Guide (New Device)

> Get the full stack running on any machine in under 15 minutes.

---

## Prerequisites

| Requirement | Version | Install |
|---|---|---|
| **Docker Desktop** | 24+ | [docker.com/get-started](https://www.docker.com/get-started) |
| **Git** | any | `brew install git` / [git-scm.com](https://git-scm.com) |
| **Ollama** | latest | [ollama.com/download](https://ollama.com/download) |

> **Windows users** — Docker Desktop requires WSL 2. Enable it from Settings → Resources → WSL Integration.

---

## Step 1 — Install & Start Ollama

Ollama runs the LLM and embedding model **on your machine** (outside Docker).

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows — download installer from https://ollama.com/download
```

Start Ollama (it runs as a background service on port 11434):

```bash
ollama serve   # macOS/Linux — skip if already running as a service
```

Pull the required models:

```bash
ollama pull qwen2.5:7b          # LLM — ~4.7 GB
ollama pull nomic-embed-text    # Embedding model — ~274 MB
```

Verify models are ready:

```bash
ollama list
# Should show: qwen2.5:7b and nomic-embed-text
```

---

## Step 2 — Clone the Repository

```bash
git clone https://github.com/varghese-ai-engineer/quizchatbot.git
cd quizchatbot
```

---

## Step 3 — Environment Configuration

The app runs with sensible defaults. No changes needed for local development:

```bash
# The .env.example is already pre-configured for local Docker
# Only copy it if you want to customise (optional for local dev)
cp .env.example .env
```

Key settings in `docker-compose.yml` (already set):

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Ollama on your host machine |
| `LLM_MODEL` | `qwen2.5:7b` | LLM for chat + quiz generation |
| `EMBED_MODEL` | `nomic-embed-text` | Embedding model for RAG |
| `DB_NAME` | `quizchatbot` | MySQL database name |
| `API_SECRET_KEY` | `change_this_...` | **Change this in production!** |

---

## Step 4 — Start All Services

```bash
docker compose up --build -d
```

This builds and starts 4 containers:

| Container | Port | Purpose |
|---|---|---|
| `quizchatbot_php` | `8090` | PHP frontend (Apache) |
| `quizchatbot_api` | `8100` | FastAPI backend |
| `quizchatbot_mysql` | `3307` | MySQL database (auto-seeded) |
| `quizchatbot_chroma` | `8200` | ChromaDB vector database |

Wait ~30 seconds for MySQL to initialise, then check all are running:

```bash
docker compose ps
# All 4 services should show "running"
```

---

## Step 5 — Ingest the Knowledge Base

Index the included `.md` files into ChromaDB so the chatbot can answer questions:

```bash
docker compose exec api python scripts/ingest_knowledge_base.py
```

You should see output like:

```
✅ Indexed: captains.md — 4 chunks
✅ Indexed: players.md — 6 chunks
✅ Indexed: teams.md — 5 chunks
...
```

---

## Step 6 — Open the App

| URL | What |
|---|---|
| **http://localhost:8090** | Main app (login / chat / quiz) |
| **http://localhost:8100/docs** | FastAPI Swagger UI |
| **http://localhost:8200** | ChromaDB API |

### Create your first account

1. Go to **http://localhost:8090**
2. Click **Sign Up** → fill in your details
3. Login → start chatting!

### Create an Admin account

```bash
docker compose exec api python scripts/create_admin.py
```

Follow the prompts. Admin accounts can:
- Upload new `.md` knowledge files
- Manage users and credits
- View the LLM Prompt Inspector

---

## Step 7 — Upload Knowledge Files (Optional)

1. Login as admin → go to **Admin → Knowledge Files**
2. Upload any `.md` file
3. The system automatically:
   - Chunks it into sections
   - Indexes embeddings into ChromaDB
   - Generates quiz questions in English, Tamil, and Hindi

---

## Troubleshooting

### `Cannot connect to Ollama`
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags
# Should return JSON with your models

# Restart if needed
ollama serve
```

### `MySQL not ready` / containers restarting
```bash
# Wait 30s then check logs
docker compose logs mysql --tail=20

# Force re-init
docker compose down -v   # ⚠️ Deletes all data
docker compose up --build -d
```

### `ChromaDB collection empty` after ingest
```bash
# Re-run ingest manually
docker compose exec api python scripts/ingest_knowledge_base.py --file captains.md
```

### Port conflicts
If 8090 / 8100 / 8200 / 3307 are already in use, edit `docker-compose.yml`:
```yaml
ports:
  - "9090:80"   # change left side only
```

### Windows — Ollama not reachable from Docker
On Windows, `host.docker.internal` may not resolve. Use your machine's IP:
```yaml
# docker-compose.yml
environment:
  - OLLAMA_HOST=http://192.168.x.x:11434   # your machine's LAN IP
```

---

## Running Tests

```bash
docker compose exec api pytest tests/ -v
# 159 tests — all should pass (3 pre-existing stubs excluded)
```

---

## Stopping & Cleanup

```bash
# Stop containers (data preserved)
docker compose down

# Stop and delete all data (fresh start)
docker compose down -v

# Remove built images too
docker compose down -v --rmi all
```

---

## File Locations Inside Containers

| Path | What |
|---|---|
| `/app/` | FastAPI backend code |
| `/app/knowledge_base/` | Uploaded `.md` files |
| `/var/www/html/` | PHP frontend |
| `mysql_data` Docker volume | MySQL database files |
| `chroma_data` Docker volume | ChromaDB vector index |
