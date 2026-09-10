import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

@dataclass
class RetrievedChunk:
    score: float
    text: str
    metadata: Dict[str, Any]

class LocalRAG:
    """Zero-cost local RAG starter. Upgrade later to FAISS + sentence-transformers."""
    def __init__(self, knowledge_path: str):
        self.docs = []
        p = Path(knowledge_path)
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self.docs.append(json.loads(line))
        self.texts = [d["text"] for d in self.docs]
        self.vectorizer = TfidfVectorizer(ngram_range=(1,2), max_features=20000, sublinear_tf=True)
        self.matrix = self.vectorizer.fit_transform(self.texts) if self.texts else None

    def search(self, query: str, top_k: int = 5) -> List[RetrievedChunk]:
        if not self.docs or not query.strip():
            return []
        qv = self.vectorizer.transform([query])
        scores = cosine_similarity(qv, self.matrix).ravel()
        out = []
        for idx in scores.argsort()[::-1]:
            if scores[idx] <= 0:
                continue
            d = self.docs[int(idx)]
            out.append(RetrievedChunk(float(scores[idx]), d["text"], d.get("metadata", {})))
            if len(out) >= top_k:
                break
        return out

def format_context(chunks: List[RetrievedChunk]) -> str:
    if not chunks:
        return "NO VERIFIED CONTEXT RETRIEVED."
    blocks=[]
    for i,c in enumerate(chunks,1):
        blocks.append(
            f"[SOURCE {i}]\nTitle: {c.metadata.get('source_title','Unknown')}\n"
            f"URL: {c.metadata.get('source_url','')}\nVerified: {c.metadata.get('verified',False)}\n"
            f"Content: {c.text}"
        )
    return "\n\n".join(blocks)
