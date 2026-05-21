"""
Ollama service — embeddings and LLM streaming.
"""
import json
from collections.abc import AsyncGenerator

import httpx

from config import settings


async def get_embedding(text: str) -> list[float]:
    """Generate embedding vector via Ollama nomic-embed-text."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.ollama_host}/api/embeddings",
            json={"model": settings.embed_model, "prompt": text},
        )
        resp.raise_for_status()
        return resp.json()["embedding"]


async def stream_llm(
    system_prompt: str,
    user_message: str,
) -> AsyncGenerator[str, None]:
    """
    Stream tokens from Ollama Llama3.
    Yields individual token strings.
    """
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=300) as client:
        try:
            async with client.stream(
                "POST",
                f"{settings.ollama_host}/api/chat",
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        token = data.get("message", {}).get("content", "")
                        if token:
                            yield token
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
        except httpx.ReadTimeout:
            yield "[LLM timeout — Llama3 took too long. Try a shorter question.]"
        except httpx.ConnectError:
            yield "[Cannot reach Ollama — is it running on localhost:11434?]"
