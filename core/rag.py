"""Asaan Qanoon AI - compact ChromaDB RAG engine.
Member 3: source curation, chunking, embeddings, retrieval and citations.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import chromadb

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "legal_sources.json"
CHROMA_DIR = ROOT / "chroma_db"
COLLECTION_NAME = "asaan_qanoon_sources"

_client = None
_collection = None


def _client_and_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _client, _collection


def load_sources() -> list[dict[str, Any]]:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def chunk_text(text: str, size: int = 700, overlap: int = 100) -> list[str]:
    """Small deterministic chunks; no external tokenizer is required."""
    text = clean_text(text)
    if not text:
        return []
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(len(words), start + size)
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(0, end - overlap)
    return chunks


def _document(source: dict[str, Any], chunk: str) -> str:
    return "\n".join(
        [
            f"Title: {source['title']}",
            f"Authority: {source['authority']}",
            f"Category: {source['category']}",
            f"Jurisdiction: {source['jurisdiction']}",
            f"Topic: {source['topic']}",
            f"Content: {chunk}",
        ]
    )


def build_index(reset: bool = False) -> int:
    """Build the persistent Chroma index from the curated JSON dataset."""
    _, collection = _client_and_collection()
    if reset and collection.count():
        collection.delete(where={})

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []

    for source in load_sources():
        for index, chunk in enumerate(chunk_text(source["content"])):
            ids.append(f"{source['id']}-chunk-{index + 1}")
            documents.append(_document(source, chunk))
            metadatas.append(
                {
                    "source_id": source["id"],
                    "title": source["title"],
                    "authority": source["authority"],
                    "category": source["category"],
                    "topic": source["topic"],
                    "jurisdiction": source["jurisdiction"],
                    "source_type": source["source_type"],
                    "source_url": source["source_url"],
                    "verified": str(source["verified"]).lower(),
                    "last_reviewed": source["last_reviewed"],
                }
            )

    if ids:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    return len(ids)


def ensure_index() -> None:
    _, collection = _client_and_collection()
    if collection.count() == 0:
        build_index()


def _keyword_score(query: str, document: str) -> float:
    q_words = {w for w in re.findall(r"[a-zA-Z0-9]+", query.lower()) if len(w) >= 3}
    d_words = set(re.findall(r"[a-zA-Z0-9]+", document.lower()))
    if not q_words:
        return 0.0
    return len(q_words & d_words) / len(q_words)


def search(query: str, top_k: int = 6, category: str | None = None) -> dict[str, Any]:
    """Hybrid-lite retrieval: Chroma semantic similarity + deterministic keyword boost."""
    query = clean_text(query)
    if len(query) < 2:
        return {"query": query, "results": [], "grounded": False}

    ensure_index()
    _, collection = _client_and_collection()
    where = {"category": category} if category else None
    result = collection.query(
        query_texts=[query],
        n_results=max(top_k, 8),
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    ranked = []

    for doc, meta, distance in zip(docs, metas, distances):
        semantic = max(0.0, min(1.0, 1.0 - float(distance)))
        keyword = _keyword_score(query, doc)
        score = round((semantic * 0.82) + (keyword * 0.18), 4)
        ranked.append(
            {
                "id": meta["source_id"],
                "title": meta["title"],
                "authority": meta["authority"],
                "category": meta["category"],
                "topic": meta["topic"],
                "jurisdiction": meta["jurisdiction"],
                "source_type": meta["source_type"],
                "source_url": meta["source_url"],
                "verified": meta["verified"] == "true",
                "last_reviewed": meta["last_reviewed"],
                "content": doc.split("Content:", 1)[-1].strip(),
                "similarity": score,
            }
        )

    ranked.sort(key=lambda item: item["similarity"], reverse=True)
    ranked = ranked[:top_k]
    grounded = bool(ranked and ranked[0]["similarity"] >= 0.32 and ranked[0]["verified"])
    return {"query": query, "results": ranked, "grounded": grounded}


def collection_count() -> int:
    _, collection = _client_and_collection()
    return collection.count()


if __name__ == "__main__":
    print(f"Indexed {build_index(reset=True)} chunks into ChromaDB.")
