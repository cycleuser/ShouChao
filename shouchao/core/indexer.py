"""
ChromaDB news indexer for ShouChao.

Indexes news articles into vector database for semantic search.
Compatible with GangDan's VectorDBBase interface.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _chunk_text(
    text: str, chunk_size: int = 800, overlap: int = 150,
) -> list[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text] if text.strip() else []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap
    return chunks


def _strip_front_matter(text: str) -> tuple[str, dict]:
    """Remove YAML front matter and return (body, metadata)."""
    meta = {}
    body = text
    if text.startswith("---"):
        end = text.find("---", 3)
        if end > 0:
            fm_block = text[3:end].strip()
            body = text[end + 3:].strip()
            for line in fm_block.split("\n"):
                if ":" in line:
                    key, _, val = line.partition(":")
                    key = key.strip()
                    val = val.strip().strip('"')
                    if val:
                        meta[key] = val
    return body, meta


class NewsIndexer:
    """Indexes news articles into ChromaDB for semantic search."""

    def __init__(
        self,
        ollama_client,
        persist_dir: Optional[str] = None,
    ):
        self.ollama = ollama_client
        if persist_dir is None:
            from shouchao.core.config import CHROMA_DIR
            persist_dir = str(CHROMA_DIR)
        self._persist_dir = persist_dir
        self._db = None

    def _get_db(self):
        """Lazy-initialize the vector database."""
        if self._db is not None:
            return self._db

        # Try GangDan's vector DB first for compatibility
        try:
            from gangdan.core.vector_db import create_vector_db_auto
            self._db = create_vector_db_auto(self._persist_dir, preferred="chroma")
            logger.info("Using GangDan vector DB backend")
            return self._db
        except ImportError:
            pass

        # Fallback: use chromadb directly
        try:
            import chromadb
            self._db = _ChromaWrapper(self._persist_dir)
            logger.info("Using direct ChromaDB backend")
            return self._db
        except ImportError:
            pass

        # Last resort: in-memory
        self._db = _InMemoryWrapper()
        logger.warning("Using in-memory vector DB (no persistence)")
        return self._db

    def _get_embedding_model(self) -> str:
        """Get the configured embedding model."""
        from shouchao.core.config import CONFIG
        if CONFIG.embedding_model:
            return CONFIG.embedding_model
        models = self.ollama.get_embedding_models()
        if models:
            CONFIG.embedding_model = models[0]
            return models[0]
        raise RuntimeError("No embedding model available in Ollama")

    def index_article(
        self,
        article_path: str | Path,
        collection: str = "shouchao_news",
    ) -> bool:
        """Index a single article into the vector database.

        Returns True on success.
        """
        path = Path(article_path)
        if not path.exists():
            logger.warning("Article not found: %s", path)
            return False

        text = path.read_text(encoding="utf-8")
        body, meta = _strip_front_matter(text)

        if not body.strip():
            return False

        db = self._get_db()
        model = self._get_embedding_model()

        from shouchao.core.config import CONFIG
        chunks = _chunk_text(body, CONFIG.chunk_size, CONFIG.chunk_overlap)
        if not chunks:
            return False

        # Build IDs and metadata for each chunk
        base_id = hashlib.md5(str(path).encode()).hexdigest()[:10]
        documents = []
        embeddings = []
        metadatas = []
        ids = []

        for i, chunk in enumerate(chunks):
            emb = self.ollama.embed(chunk, model)
            if emb is None:
                logger.warning("Embedding failed for chunk %d of %s", i, path)
                continue

            chunk_meta = {
                "source": "shouchao",
                "language": meta.get("language", ""),
                "website": meta.get("website", ""),
                "date": meta.get("date", meta.get("published", "")),
                "title": meta.get("title", path.stem),
                "url": meta.get("url", ""),
                "category": meta.get("category", ""),
                "chunk_index": i,
                "total_chunks": len(chunks),
                "file_path": str(path),
            }

            documents.append(chunk)
            embeddings.append(emb)
            metadatas.append(chunk_meta)
            ids.append(f"{base_id}_{i}")

        if not documents:
            return False

        try:
            db.get_or_create_collection(collection)
            db.add_documents(collection, documents, embeddings, metadatas, ids)
            logger.debug("Indexed %d chunks from %s", len(documents), path)
            return True
        except Exception as e:
            logger.error("Failed to index %s: %s", path, e)
            return False

    def index_directory(
        self,
        dir_path: str | Path,
        collection: str = "shouchao_news",
    ) -> int:
        """Index all .md files in a directory tree. Returns count indexed."""
        dir_path = Path(dir_path)
        count = 0
        for md_file in sorted(dir_path.rglob("*.md")):
            if self.index_article(md_file, collection):
                count += 1
        return count

    def search_news(
        self,
        query: str,
        language: str = None,
        date_from: str = None,
        date_to: str = None,
        category: str = None,
        collection: str = "shouchao_news",
        top_k: int = 10,
    ) -> list[dict]:
        """Semantic search across indexed news.

        Returns list of {id, document, metadata, distance}.
        """
        db = self._get_db()
        model = self._get_embedding_model()

        emb = self.ollama.embed(query, model)
        if emb is None:
            return []

        try:
            if not db.collection_exists(collection):
                return []
            results = db.search(collection, emb, top_k=top_k * 2)
        except Exception as e:
            logger.error("Search failed: %s", e)
            return []

        # Post-filter by metadata
        filtered = []
        for r in results:
            m = r.get("metadata", {})
            if language and m.get("language") != language:
                continue
            if category and category not in m.get("category", ""):
                continue
            if date_from and m.get("date", "") < date_from:
                continue
            if date_to and m.get("date", "") > date_to:
                continue
            filtered.append(r)
            if len(filtered) >= top_k:
                break

        return filtered

    def get_stats(self, collection: str = "shouchao_news") -> dict:
        """Get index statistics."""
        db = self._get_db()
        try:
            return db.get_stats()
        except Exception:
            return {}

    def get_document_count(self, collection: str = "shouchao_news") -> int:
        """Get total number of indexed documents."""
        stats = self.get_stats(collection)
        return stats.get("count", 0)


# ---------------------------------------------------------------------------
# Minimal ChromaDB wrapper (GangDan-compatible interface)
# ---------------------------------------------------------------------------

class _ChromaWrapper:
    """Thin wrapper matching GangDan's VectorDBBase interface."""

    def __init__(self, persist_dir: str):
        import chromadb
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collections: dict = {}

    def get_or_create_collection(self, name: str):
        if name not in self._collections:
            self._collections[name] = self._client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[name]

    def collection_exists(self, name: str) -> bool:
        try:
            existing = [c.name for c in self._client.list_collections()]
            return name in existing
        except Exception:
            return False

    def add_documents(self, collection_name, documents, embeddings,
                      metadatas, ids) -> bool:
        coll = self.get_or_create_collection(collection_name)
        # Filter out non-string metadata values
        clean_meta = []
        for m in metadatas:
            clean = {}
            for k, v in m.items():
                if isinstance(v, (str, int, float, bool)):
                    clean[k] = v
                else:
                    clean[k] = str(v)
            clean_meta.append(clean)
        coll.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=clean_meta,
            ids=ids,
        )
        return True

    def search(self, collection_name, query_embedding, top_k=10):
        coll = self.get_or_create_collection(collection_name)
        result = coll.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        items = []
        if result["ids"] and result["ids"][0]:
            for i, doc_id in enumerate(result["ids"][0]):
                items.append({
                    "id": doc_id,
                    "document": result["documents"][0][i],
                    "metadata": result["metadatas"][0][i],
                    "distance": result["distances"][0][i],
                })
        return items

    def list_collections(self):
        return [c.name for c in self._client.list_collections()]

    def get_stats(self):
        stats = {}
        for c in self._client.list_collections():
            stats[c.name] = c.count()
        return stats

    def delete_collection(self, name):
        try:
            self._client.delete_collection(name)
            self._collections.pop(name, None)
            return True
        except Exception:
            return False

    def get_documents(self, collection_name, limit=0, include=None):
        coll = self.get_or_create_collection(collection_name)
        inc = include or ["documents", "metadatas"]
        kwargs = {"include": inc}
        if limit > 0:
            kwargs["limit"] = limit
        result = coll.get(**kwargs)
        return result


class _InMemoryWrapper:
    """In-memory vector DB for when ChromaDB isn't available."""

    def __init__(self):
        self._collections: dict[str, dict] = {}

    def get_or_create_collection(self, name):
        if name not in self._collections:
            self._collections[name] = {
                "ids": [], "documents": [], "embeddings": [],
                "metadatas": [],
            }
        return self._collections[name]

    def collection_exists(self, name):
        return name in self._collections

    def add_documents(self, collection_name, documents, embeddings,
                      metadatas, ids):
        coll = self.get_or_create_collection(collection_name)
        coll["ids"].extend(ids)
        coll["documents"].extend(documents)
        coll["embeddings"].extend(embeddings)
        coll["metadatas"].extend(metadatas)
        return True

    def search(self, collection_name, query_embedding, top_k=10):
        import numpy as np
        coll = self.get_or_create_collection(collection_name)
        if not coll["embeddings"]:
            return []
        q = np.array(query_embedding)
        q_norm = q / (np.linalg.norm(q) + 1e-10)
        results = []
        for i, emb in enumerate(coll["embeddings"]):
            e = np.array(emb)
            e_norm = e / (np.linalg.norm(e) + 1e-10)
            dist = 1.0 - float(np.dot(q_norm, e_norm))
            results.append((i, dist))
        results.sort(key=lambda x: x[1])
        items = []
        for idx, dist in results[:top_k]:
            items.append({
                "id": coll["ids"][idx],
                "document": coll["documents"][idx],
                "metadata": coll["metadatas"][idx],
                "distance": dist,
            })
        return items

    def list_collections(self):
        return list(self._collections.keys())

    def get_stats(self):
        return {k: len(v["ids"]) for k, v in self._collections.items()}

    def delete_collection(self, name):
        self._collections.pop(name, None)
        return True

    def get_documents(self, collection_name, limit=0, include=None):
        coll = self.get_or_create_collection(collection_name)
        if limit > 0:
            return {k: v[:limit] for k, v in coll.items()}
        return dict(coll)
