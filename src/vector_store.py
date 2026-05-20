import json
from math import sqrt

from src.ai import AiClient
from src.config import Settings
from src.schemas import DocumentChunk, RetrievedChunk


COLLECTION_NAME = "support_knowledge"


class VectorStore:
    def __init__(self, settings: Settings, ai_client: AiClient):
        self.settings = settings
        self.ai_client = ai_client
        self.backend = settings.vector_store_backend
        self.store_dir = settings.vector_store_dir
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.store_path = self.store_dir / "support_knowledge.json"

        if self.backend == "chroma":
            import chromadb

            self.client = chromadb.PersistentClient(path=str(self.store_dir))
            self.collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        elif self.backend == "json":
            self.client = None
            self.collection = None
        else:
            raise ValueError("VECTOR_STORE_BACKEND must be 'chroma' or 'json'")

    def upsert_chunks(self, chunks: list[DocumentChunk]) -> int:
        if not chunks:
            return 0
        if self.backend == "chroma":
            return self._upsert_chroma(chunks)
        return self._upsert_json(chunks)

    def search(self, query: str, limit: int = 5) -> list[RetrievedChunk]:
        if self.backend == "chroma":
            return self._search_chroma(query, limit)
        return self._search_json(query, limit)

    def clear(self) -> None:
        if self.backend == "chroma":
            assert self.client is not None
            try:
                self.client.delete_collection(COLLECTION_NAME)
            except Exception:
                pass
            self.collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            return

        if self.store_path.exists():
            self.store_path.unlink()

    def close(self) -> None:
        self.collection = None
        self.client = None

    def _upsert_chroma(self, chunks: list[DocumentChunk]) -> int:
        assert self.collection is not None
        embeddings = self.ai_client.embed_texts([chunk.text for chunk in chunks])
        self.collection.upsert(
            ids=[chunk.id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            metadatas=[_clean_metadata(chunk.metadata) for chunk in chunks],
            embeddings=embeddings,
        )
        return len(chunks)

    def _search_chroma(self, query: str, limit: int) -> list[RetrievedChunk]:
        assert self.collection is not None
        query_embedding = self.ai_client.embed_texts([query])[0]
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            include=["documents", "metadatas", "distances"],
        )
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        chunks: list[RetrievedChunk] = []
        for document, metadata, distance in zip(documents, metadatas, distances):
            chunks.append(
                RetrievedChunk(
                    text=document,
                    score=max(0.0, 1.0 - float(distance)),
                    metadata=metadata or {},
                )
            )
        return chunks

    def _upsert_json(self, chunks: list[DocumentChunk]) -> int:
        records = self._load_records()
        by_id = {record["id"]: record for record in records}
        embeddings = self.ai_client.embed_texts([chunk.text for chunk in chunks])
        for chunk, embedding in zip(chunks, embeddings):
            by_id[chunk.id] = {
                "id": chunk.id,
                "text": chunk.text,
                "metadata": _clean_metadata(chunk.metadata),
                "embedding": embedding,
            }
        self._save_records(list(by_id.values()))
        return len(chunks)

    def _search_json(self, query: str, limit: int) -> list[RetrievedChunk]:
        query_embedding = self.ai_client.embed_texts([query])[0]
        scored = []
        for record in self._load_records():
            score = _cosine_similarity(query_embedding, record["embedding"])
            scored.append((score, record))
        scored.sort(key=lambda item: item[0], reverse=True)

        chunks: list[RetrievedChunk] = []
        for score, record in scored[:limit]:
            chunks.append(
                RetrievedChunk(
                    text=record["text"],
                    score=max(0.0, score),
                    metadata=record.get("metadata") or {},
                )
            )
        return chunks

    def _load_records(self) -> list[dict]:
        if not self.store_path.exists():
            return []
        return json.loads(self.store_path.read_text(encoding="utf-8"))

    def _save_records(self, records: list[dict]) -> None:
        self.store_path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = sqrt(sum(a * a for a in left)) or 1.0
    right_norm = sqrt(sum(b * b for b in right)) or 1.0
    return dot / (left_norm * right_norm)


def _clean_metadata(metadata: dict) -> dict[str, str | int | float | bool]:
    return {
        key: value
        for key, value in metadata.items()
        if isinstance(value, str | int | float | bool)
    }
