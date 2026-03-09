"""
Ollama API client for ShouChao.

Provides embedding generation and chat completion via Ollama.
Adapted from GangDan's ollama_client pattern.
"""

import json
import logging
from typing import Optional, Iterator

import requests

logger = logging.getLogger(__name__)

# Patterns to identify embedding models
_EMBED_PATTERNS = (
    "embed", "nomic-embed", "bge-", "e5-", "gte-",
    "instructor", "sentence", "all-minilm",
)


class OllamaClient:
    """Client for Ollama API (local LLM inference)."""

    def __init__(self, api_url: str = "http://localhost:11434"):
        self.api_url = api_url.rstrip("/")

    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            resp = requests.get(f"{self.api_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def get_models(self) -> list[dict]:
        """List all available models."""
        try:
            resp = requests.get(f"{self.api_url}/api/tags", timeout=10)
            resp.raise_for_status()
            return resp.json().get("models", [])
        except Exception as e:
            logger.warning("Failed to list models: %s", e)
            return []

    def get_embedding_models(self) -> list[str]:
        """Find embedding-capable models."""
        models = self.get_models()
        results = []
        for m in models:
            name = m.get("name", "").lower()
            if any(p in name for p in _EMBED_PATTERNS):
                results.append(m["name"])
        return results

    def get_chat_models(self) -> list[str]:
        """Find chat-capable models (non-embedding)."""
        models = self.get_models()
        embed_set = set(self.get_embedding_models())
        return [m["name"] for m in models if m["name"] not in embed_set]

    def embed(self, text: str, model: str) -> Optional[list[float]]:
        """Generate embedding for text.

        Returns:
            List of floats (embedding vector) or None on error.
        """
        try:
            resp = requests.post(
                f"{self.api_url}/api/embed",
                json={"model": model, "input": text},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            embeddings = data.get("embeddings")
            if embeddings and len(embeddings) > 0:
                return embeddings[0]
            return None
        except Exception as e:
            logger.error("Embedding failed: %s", e)
            return None

    def chat_stream(
        self,
        messages: list[dict],
        model: str,
    ) -> Iterator[str]:
        """Streaming chat completion. Yields text chunks."""
        try:
            resp = requests.post(
                f"{self.api_url}/api/chat",
                json={"model": model, "messages": messages, "stream": True},
                stream=True,
                timeout=120,
            )
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if data.get("done"):
                        break
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            logger.error("Chat stream failed: %s", e)
            yield f"\n[Error: {e}]"

    def chat_complete(
        self,
        messages: list[dict],
        model: str,
    ) -> str:
        """Non-streaming chat completion. Returns full response."""
        try:
            resp = requests.post(
                f"{self.api_url}/api/chat",
                json={"model": model, "messages": messages, "stream": False},
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json().get("message", {}).get("content", "")
        except Exception as e:
            logger.error("Chat complete failed: %s", e)
            return f"[Error: {e}]"
