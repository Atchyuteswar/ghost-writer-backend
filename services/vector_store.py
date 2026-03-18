# services/vector_store.py — complete rewrite

from sentence_transformers import SentenceTransformer
import numpy as np
from models.schemas import ParsedMessage, MemoryResult
from config import settings
import uuid
from datetime import datetime

class VectorStore:
    _instance = None
    _model = None
    _local_store: list[dict] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            VectorStore._model = SentenceTransformer('all-MiniLM-L6-v2')
        self._pinecone_available = False
        self._index = None
        if not settings.LOCAL_ONLY_MODE and settings.PINECONE_API_KEY:
            try:
                from pinecone import Pinecone
                pc = Pinecone(api_key=settings.PINECONE_API_KEY)
                self._index = pc.Index(settings.PINECONE_INDEX_NAME)
                self._pinecone_available = True
            except Exception as e:
                print(f"Pinecone unavailable, falling back to local: {e}")

    def _chunk_message(self, message: ParsedMessage) -> list[dict]:
        """
        Split a message into semantic chunks.
        Rules:
        - If message is under 20 words: keep as one chunk
        - If message is 20-60 words: split at sentence boundaries
        - If message is over 60 words: split into 40-word overlapping windows
          with 10-word overlap to preserve context across boundaries
        """
        words = message.text.split()
        word_count = len(words)
        chunks = []

        if word_count < 20:
            # Single chunk
            chunks.append({
                "text": message.text,
                "chunk_index": 0,
                "total_chunks": 1
            })
        elif word_count < 60:
            # Split at sentence boundaries using period, question mark, exclamation
            import re
            sentences = re.split(r'(?<=[.!?])\s+', message.text)
            current_chunk = ""
            chunk_index = 0
            for sentence in sentences:
                if len((current_chunk + " " + sentence).split()) > 30 and current_chunk:
                    chunks.append({
                        "text": current_chunk.strip(),
                        "chunk_index": chunk_index,
                        "total_chunks": 0  # updated after
                    })
                    chunk_index += 1
                    current_chunk = sentence
                else:
                    current_chunk += " " + sentence
            if current_chunk.strip():
                chunks.append({
                    "text": current_chunk.strip(),
                    "chunk_index": chunk_index,
                    "total_chunks": 0
                })
        else:
            # Sliding window: 40-word windows with 10-word overlap
            window_size = 40
            overlap = 10
            step = window_size - overlap
            chunk_index = 0
            for i in range(0, word_count, step):
                window = words[i:i + window_size]
                if len(window) < 5:
                    break
                chunks.append({
                    "text": " ".join(window),
                    "chunk_index": chunk_index,
                    "total_chunks": 0
                })
                chunk_index += 1

        # Update total_chunks
        total = len(chunks)
        for chunk in chunks:
            chunk["total_chunks"] = total

        return chunks

    def store_memories(self, messages: list[ParsedMessage]) -> int:
        stored_count = 0
        for message in messages:
            # Only store messages with meaningful content
            if len(message.text.split()) < 5:
                continue
            # Skip system-like messages
            if message.text.startswith("[") and message.text.endswith("]"):
                continue

            chunks = self._chunk_message(message)
            for chunk in chunks:
                embedding = self._model.encode(chunk["text"]).tolist()
                memory_id = str(uuid.uuid4())
                record = {
                    "id": memory_id,
                    "text": chunk["text"],
                    "original_message_id": message.id,
                    "embedding": embedding,
                    "date": message.timestamp[:10],  # YYYY-MM-DD
                    "platform": message.platform,
                    "sender": message.sender,
                    "chunk_index": chunk["chunk_index"],
                    "total_chunks": chunk["total_chunks"]
                }
                if self._pinecone_available:
                    self._index.upsert(vectors=[{
                        "id": memory_id,
                        "values": embedding,
                        "metadata": {
                            "text": chunk["text"],
                            "date": record["date"],
                            "platform": message.platform,
                            "sender": message.sender
                        }
                    }])
                else:
                    VectorStore._local_store.append(record)
                stored_count += 1

        return stored_count

    def search(self, query: str, top_k: int = 5) -> list[MemoryResult]:
        query_embedding = self._model.encode(query).tolist()

        if self._pinecone_available:
            results = self._index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )
            return [
                MemoryResult(
                    text=match["metadata"]["text"],
                    score=round(match["score"], 4),
                    date=match["metadata"].get("date", ""),
                    platform=match["metadata"].get("platform", "unknown")
                )
                for match in results["matches"]
            ]
        else:
            if not VectorStore._local_store:
                return []
            # Cosine similarity search
            scores = []
            query_arr = np.array(query_embedding)
            for record in VectorStore._local_store:
                stored_arr = np.array(record["embedding"])
                norm_product = np.linalg.norm(query_arr) * np.linalg.norm(stored_arr)
                if norm_product == 0:
                    score = 0.0
                else:
                    score = float(np.dot(query_arr, stored_arr) / norm_product)
                scores.append((score, record))

            # Sort by score descending, return top_k
            scores.sort(key=lambda x: x[0], reverse=True)
            top_results = scores[:top_k]

            return [
                MemoryResult(
                    text=record["text"],
                    score=round(score, 4),
                    date=record["date"],
                    platform=record["platform"]
                )
                for score, record in top_results
                if score > 0.2  # filter out very low relevance results
            ]

    def get_count(self) -> int:
        if self._pinecone_available:
            stats = self._index.describe_index_stats()
            return stats["total_vector_count"]
        return len(VectorStore._local_store)

    def clear(self) -> bool:
        if self._pinecone_available:
            self._index.delete(delete_all=True)
        VectorStore._local_store = []
        return True

    @property
    def mode(self) -> str:
        return "pinecone" if self._pinecone_available else "local"

    @property
    def count(self) -> int:
        return self.get_count()

def get_vector_store() -> VectorStore:
    """Helper for FastAPI routers to get the singleton VectorStore."""
    return VectorStore()