"""ChromaDB-backed cache for scraped interview signals, with a 24h TTL."""
import json
import os
import time
from typing import Optional

import chromadb

TTL_SECONDS = 24 * 60 * 60
COLLECTION_NAME = "interview_signals"


class SignalCache:
    def __init__(self, persist_path: Optional[str] = None):
        persist_path = persist_path or os.environ.get("CHROMA_PERSIST_PATH", "./chroma_data")
        self._client = chromadb.PersistentClient(path=persist_path)
        self._collection = self._client.get_or_create_collection(COLLECTION_NAME)

    @staticmethod
    def _doc_id(company: str, role: str) -> str:
        return f"{company.strip().lower()}::{role.strip().lower()}"

    def get(self, company: str, role: str) -> Optional[dict]:
        doc_id = self._doc_id(company, role)
        result = self._collection.get(ids=[doc_id], include=["metadatas", "documents"])
        if not result["ids"]:
            return None
        metadata = result["metadatas"][0]
        cached_at = metadata.get("cached_at", 0)
        if time.time() - cached_at > TTL_SECONDS:
            return None
        return json.loads(result["documents"][0])

    def set(self, company: str, role: str, signals: dict) -> None:
        doc_id = self._doc_id(company, role)
        self._collection.upsert(
            ids=[doc_id],
            documents=[json.dumps(signals)],
            metadatas=[{"cached_at": time.time(), "company": company, "role": role}],
        )

    def is_fresh(self, company: str, role: str) -> bool:
        return self.get(company, role) is not None
