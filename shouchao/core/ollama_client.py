"""
Ollama API client for ShouChao.

Provides embedding generation and chat completion via Ollama.
Adapted from GangDan's ollama_client pattern.

IMPORTANT: Ollama is a local service, so we explicitly disable proxy
to avoid issues when system proxy is configured.
"""

import json
import logging
import os
from typing import Optional, Iterator

import requests

logger = logging.getLogger(__name__)

_PATTERNS = (
    "embed", "nomic-embed", "bge-", "e5-", "gte-",
    "instructor", "sentence", "all-minilm",
)

DEFAULT_TIMEOUT = 300  # 5 minutes for large models


class OllamaClient:
    """Client for Ollama API (local LLM inference)."""

    def __init__(self, api_url: str = "http://localhost:11434", timeout: int = DEFAULT_TIMEOUT):
        self.api_url = api_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.trust_env = False

    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            resp = self._session.get(
                f"{self.api_url}/api/tags",
                timeout=10,
            )
            return resp.status_code == 200
        except requests.exceptions.ConnectionError:
            logger.debug("Ollama not running at %s", self.api_url)
            return False
        except Exception as e:
            logger.warning("Ollama availability check failed: %s", e)
            return False

    def get_models(self) -> list[dict]:
        """List all available models."""
        try:
            resp = self._session.get(
                f"{self.api_url}/api/tags",
                timeout=30,
            )
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
            if any(p in name for p in _PATTERNS):
                results.append(m["name"])
        return results

    def get_chat_models(self) -> list[str]:
        """Find chat-capable models (non-embedding)."""
        models = self.get_models()
        embed_set = set(self.get_embedding_models())
        return [m["name"] for m in models if m["name"] not in embed_set]

    def embed(self, text: str, model: str) -> Optional[list[float]]:
        """Generate embedding for text."""
        try:
            resp = self._session.post(
                f"{self.api_url}/api/embeddings",
                json={"model": model, "prompt": text},
                timeout=self._timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                embedding = data.get("embedding")
                if embedding:
                    return embedding
            resp = self._session.post(
                f"{self.api_url}/api/embed",
                json={"model": model, "input": text},
                timeout=self._timeout,
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
            resp = self._session.post(
                f"{self.api_url}/api/chat",
                json={"model": model, "messages": messages, "stream": True},
                stream=True,
                timeout=self._timeout,
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
            logger.info("Calling Ollama chat API with model: %s", model)
            resp = self._session.post(
                f"{self.api_url}/api/chat",
                json={"model": model, "messages": messages, "stream": False},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            result = resp.json().get("message", {}).get("content", "")
            logger.info("Ollama response length: %d chars", len(result))
            return result
        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out after %d seconds", self._timeout)
            return f"[Error: Request timed out. Try using a smaller/faster model.]"
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to Ollama at %s", self.api_url)
            return f"[Error: Cannot connect to Ollama. Is it running?]"
        except Exception as e:
            logger.error("Chat complete failed: %s", e)
            return f"[Error: {e}]"
