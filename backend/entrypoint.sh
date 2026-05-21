#!/bin/bash
# ============================================================
# QuizChatbot Backend Entrypoint
# 1. Wait for MySQL to be ready
# 2. Wait for ChromaDB to be ready
# 3. Run knowledge base ingest (skip already-indexed files)
# 4. Start FastAPI server
# ============================================================

set -e

echo "⏳ Waiting for MySQL..."
until python -c "
import pymysql, os, time
for i in range(30):
    try:
        pymysql.connect(
            host=os.getenv('DB_HOST','mysql'),
            port=int(os.getenv('DB_PORT','3306')),
            user=os.getenv('DB_USER','quizuser'),
            password=os.getenv('DB_PASS','quizpass'),
            database=os.getenv('DB_NAME','quizchatbot')
        )
        break
    except Exception:
        time.sleep(2)
" 2>/dev/null; do
    sleep 2
done
echo "✅ MySQL ready."

echo "⏳ Waiting for ChromaDB..."
until python -c "
import httpx, os, time
for i in range(30):
    try:
        r = httpx.get(f\"http://{os.getenv('CHROMA_HOST','chromadb')}:{os.getenv('CHROMA_PORT','8000')}/api/v1/heartbeat\", timeout=3)
        if r.status_code == 200:
            break
    except Exception:
        pass
    time.sleep(2)
" 2>/dev/null; do
    sleep 2
done
echo "✅ ChromaDB ready."

echo "📚 Running knowledge base ingest (incremental)..."
python scripts/ingest_knowledge_base.py || echo "⚠️  Ingest failed — continuing startup."

echo "🚀 Starting FastAPI server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
