from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import chromadb


# ============================================================
# Paths
# ============================================================

# core/rag.py
CORE_DIR = Path(__file__).resolve().parent

# project root
ROOT = CORE_DIR.parent

DATA_FILE = ROOT / "data" / "legal_sources.json"

CHROMA_DIR = ROOT / "chroma_db"

COLLECTION_NAME = "asaan_qanoon_sources"


_client = None
_collection = None


# ============================================================
# Chroma client
# ============================================================

def _client_and_collection():

    global _client, _collection

    if _collection is None:

        _client = chromadb.PersistentClient(
            path=str(CHROMA_DIR)
        )

        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={
                "hnsw:space": "cosine"
            },
        )

    return _client, _collection


# ============================================================
# Load legal sources
# ============================================================

def load_sources() -> list[dict[str, Any]]:

    if not DATA_FILE.exists():

        raise FileNotFoundError(
            f"Legal dataset not found at: {DATA_FILE}"
        )

    return json.loads(
        DATA_FILE.read_text(
            encoding="utf-8"
        )
    )


# ============================================================
# Text cleaning
# ============================================================

def clean_text(text: str) -> str:

    return re.sub(
        r"\s+",
        " ",
        text or "",
    ).strip()


# ============================================================
# Chunking
# ============================================================

def chunk_text(
    text: str,
    size: int = 700,
    overlap: int = 100,
) -> list[str]:

    text = clean_text(text)

    if not text:
        return []

    words = text.split()

    chunks = []

    start = 0

    while start < len(words):

        end = min(
            len(words),
            start + size,
        )

        chunk = " ".join(
            words[start:end]
        )

        chunks.append(chunk)

        if end == len(words):
            break

        start = max(
            0,
            end - overlap,
        )

    return chunks


# ============================================================
# Build document text
# ============================================================

def _document(
    source: dict[str, Any],
    chunk: str,
) -> str:

    return "\n".join(
        [
            f"Title: {source.get('title', '')}",
            f"Authority: {source.get('authority', '')}",
            f"Category: {source.get('category', '')}",
            f"Jurisdiction: {source.get('jurisdiction', '')}",
            f"Topic: {source.get('topic', '')}",
            f"Content: {chunk}",
        ]
    )


# ============================================================
# Build Chroma index
# ============================================================

def build_index(
    reset: bool = False
) -> int:

    _, collection = _client_and_collection()

    if reset and collection.count() > 0:

        existing = collection.get()

        existing_ids = existing.get(
            "ids",
            []
        )

        if existing_ids:
            collection.delete(
                ids=existing_ids
            )

    ids = []
    documents = []
    metadatas = []

    sources = load_sources()

    for source in sources:

        chunks = chunk_text(
            source.get(
                "content",
                ""
            )
        )

        for index, chunk in enumerate(
            chunks
        ):

            chunk_id = (
                f"{source['id']}"
                f"-chunk-{index + 1}"
            )

            ids.append(
                chunk_id
            )

            documents.append(
                _document(
                    source,
                    chunk,
                )
            )

            metadatas.append(
                {
                    "source_id":
                        source.get(
                            "id",
                            ""
                        ),

                    "title":
                        source.get(
                            "title",
                            ""
                        ),

                    "authority":
                        source.get(
                            "authority",
                            ""
                        ),

                    "category":
                        source.get(
                            "category",
                            ""
                        ),

                    "topic":
                        source.get(
                            "topic",
                            ""
                        ),

                    "jurisdiction":
                        source.get(
                            "jurisdiction",
                            "Pakistan"
                        ),

                    "source_type":
                        source.get(
                            "source_type",
                            ""
                        ),

                    "source_url":
                        source.get(
                            "source_url",
                            ""
                        ),

                    "verified":
                        str(
                            source.get(
                                "verified",
                                False,
                            )
                        ).lower(),

                    "last_reviewed":
                        source.get(
                            "last_reviewed",
                            ""
                        ),
                }
            )

    if ids:

        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

    return len(ids)


# ============================================================
# Ensure index exists
# ============================================================

def ensure_index():

    _, collection = _client_and_collection()

    if collection.count() == 0:

        build_index(
            reset=False
        )


# ============================================================
# Keyword score
# ============================================================

def _keyword_score(
    query: str,
    document: str,
) -> float:

    query_words = {
        word
        for word in re.findall(
            r"[a-zA-Z0-9]+",
            query.lower(),
        )
        if len(word) >= 3
    }

    document_words = set(
        re.findall(
            r"[a-zA-Z0-9]+",
            document.lower(),
        )
    )

    if not query_words:
        return 0.0

    matches = (
        query_words
        & document_words
    )

    return (
        len(matches)
        / len(query_words)
    )


# ============================================================
# Search
# ============================================================

def search(
    query: str,
    top_k: int = 6,
    category: str | None = None,
    jurisdiction: str | None = None,
) -> dict[str, Any]:

    query = clean_text(query)

    if len(query) < 2:

        return {
            "query": query,
            "results": [],
            "grounded": False,
        }

    ensure_index()

    _, collection = _client_and_collection()

    # ----------------------------------------
    # Metadata filtering
    # ----------------------------------------

    filters = []

    if category:

        filters.append(
            {
                "category": category
            }
        )

    if jurisdiction:

        filters.append(
            {
                "jurisdiction":
                    jurisdiction
            }
        )

    where = None

    if len(filters) == 1:

        where = filters[0]

    elif len(filters) > 1:

        where = {
            "$and": filters
        }

    # ----------------------------------------
    # Query Chroma
    # ----------------------------------------

    try:

        result = collection.query(
            query_texts=[
                query
            ],
            n_results=max(
                top_k,
                8,
            ),
            where=where,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

    except Exception:

        # If strict jurisdiction filtering
        # returns nothing or fails,
        # retry with category only.

        fallback_where = (
            {
                "category":
                    category
            }
            if category
            else None
        )

        result = collection.query(
            query_texts=[
                query
            ],
            n_results=max(
                top_k,
                8,
            ),
            where=fallback_where,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

    documents = (
        result.get(
            "documents"
        )
        or [[]]
    )[0]

    metadatas = (
        result.get(
            "metadatas"
        )
        or [[]]
    )[0]

    distances = (
        result.get(
            "distances"
        )
        or [[]]
    )[0]

    ranked = []

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances,
    ):

        semantic_score = max(
            0.0,
            min(
                1.0,
                1.0 - float(
                    distance
                ),
            ),
        )

        keyword_score = (
            _keyword_score(
                query,
                document,
            )
        )

        final_score = round(
            (
                semantic_score * 0.82
            )
            +
            (
                keyword_score * 0.18
            ),
            4,
        )

        content = document

        if "Content:" in document:

            content = document.split(
                "Content:",
                1,
            )[-1].strip()

        ranked.append(
            {
                "id":
                    metadata.get(
                        "source_id",
                        ""
                    ),

                "title":
                    metadata.get(
                        "title",
                        ""
                    ),

                "authority":
                    metadata.get(
                        "authority",
                        ""
                    ),

                "category":
                    metadata.get(
                        "category",
                        ""
                    ),

                "topic":
                    metadata.get(
                        "topic",
                        ""
                    ),

                "jurisdiction":
                    metadata.get(
                        "jurisdiction",
                        ""
                    ),

                "source_type":
                    metadata.get(
                        "source_type",
                        ""
                    ),

                "source_url":
                    metadata.get(
                        "source_url",
                        ""
                    ),

                "verified":
                    (
                        metadata.get(
                            "verified",
                            "false"
                        )
                        == "true"
                    ),

                "last_reviewed":
                    metadata.get(
                        "last_reviewed",
                        ""
                    ),

                "content":
                    content,

                "similarity":
                    final_score,
            }
        )

    ranked.sort(
        key=lambda item:
            item["similarity"],
        reverse=True,
    )

    ranked = ranked[
        :top_k
    ]

    grounded = bool(
        ranked
        and ranked[0][
            "similarity"
        ] >= 0.32
        and ranked[0][
            "verified"
        ]
    )

    return {
        "query": query,
        "results": ranked,
        "grounded": grounded,
    }


# ============================================================
# Backward-compatible retrieve()
# ============================================================

def retrieve(
    query: str,
    top_k: int = 6,
    category: str | None = None,
):

    """
    Compatibility wrapper for older agents.py code.
    """

    result = search(
        query=query,
        top_k=top_k,
        category=category,
    )

    return result[
        "results"
    ]


# ============================================================
# Format retrieved context for LLM
# ============================================================

def format_context(
    results: list[dict]
) -> str:

    if not results:

        return (
            "No sufficiently relevant "
            "verified legal sources were retrieved."
        )

    blocks = []

    for index, item in enumerate(
        results,
        start=1,
    ):

        block = (
            f"[SOURCE {index}]\n"
            f"Title: {item.get('title', '')}\n"
            f"Authority: {item.get('authority', '')}\n"
            f"Category: {item.get('category', '')}\n"
            f"Jurisdiction: {item.get('jurisdiction', '')}\n"
            f"Verified: {item.get('verified', False)}\n"
            f"Similarity: {item.get('similarity', 0)}\n"
            f"URL: {item.get('source_url', '')}\n"
            f"Content: {item.get('content', '')}"
        )

        blocks.append(
            block
        )

    return "\n\n".join(
        blocks
    )


# ============================================================
# Collection statistics
# ============================================================

def collection_count() -> int:

    _, collection = _client_and_collection()

    return collection.count()


def dataset_count() -> int:

    return len(
        load_sources()
    )


# ============================================================
# Manual test
# ============================================================

if __name__ == "__main__":

    count = build_index(
        reset=True
    )

    print(
        f"Indexed {count} chunks."
    )

    result = search(
        "mera CNIC expire hogaya hai renewal kaise hoga"
    )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )
