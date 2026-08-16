"""RAG pipeline: chunk docs -> TF-IDF index -> retrieve -> grounded answer.

TF-IDF keeps retrieval fully local (no embedding API needed), deterministic,
and fast (well under the 2s latency target). The interface is intentionally
simple so it can later be swapped for vector embeddings + a vector DB.
"""
from __future__ import annotations

import os
import pickle
import re
from dataclasses import dataclass

import config
from src import llm


@dataclass
class Chunk:
    doc: str
    text: str


def _split_into_chunks(text: str, max_chars: int = 700) -> list[str]:
    """Split on blank lines, then pack paragraphs up to max_chars."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, buf = [], ""
    for p in paras:
        if len(buf) + len(p) + 1 <= max_chars:
            buf = f"{buf}\n{p}".strip()
        else:
            if buf:
                chunks.append(buf)
            buf = p
    if buf:
        chunks.append(buf)
    return chunks


def build_index() -> int:
    """Read every doc in DOCS_DIR, build a TF-IDF matrix, pickle it. Returns #chunks."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    chunks: list[Chunk] = []
    for fname in sorted(os.listdir(config.DOCS_DIR)):
        if not fname.endswith((".md", ".txt")):
            continue
        text = (config.DOCS_DIR / fname).read_text(encoding="utf-8")
        for c in _split_into_chunks(text):
            chunks.append(Chunk(doc=fname, text=c))

    if not chunks:
        raise RuntimeError("No documents found to index in data/docs.")

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    matrix = vectorizer.fit_transform([c.text for c in chunks])
    with open(config.INDEX_PATH, "wb") as fh:
        pickle.dump({"vectorizer": vectorizer, "matrix": matrix, "chunks": chunks}, fh)
    return len(chunks)


_INDEX_CACHE = None


def _load_index():
    global _INDEX_CACHE
    if _INDEX_CACHE is None:
        if not os.path.exists(config.INDEX_PATH):
            build_index()
        with open(config.INDEX_PATH, "rb") as fh:
            _INDEX_CACHE = pickle.load(fh)
    return _INDEX_CACHE


def retrieve(query: str, top_k: int | None = None):
    """Return list of (Chunk, similarity) sorted by relevance."""
    from sklearn.metrics.pairwise import cosine_similarity

    top_k = top_k or config.RAG_TOP_K
    idx = _load_index()
    q_vec = idx["vectorizer"].transform([query])
    sims = cosine_similarity(q_vec, idx["matrix"])[0]
    ranked = sorted(zip(idx["chunks"], sims), key=lambda x: x[1], reverse=True)
    return ranked[:top_k]


_ANSWER_SYSTEM = (
    "You are a concise, friendly medical-equipment support assistant. "
    "Answer the user's question using ONLY the provided context passages. "
    "If the context does not contain the answer, reply exactly: "
    f"'{config.FALLBACK_MESSAGE}'. Cite the source document name in parentheses. "
    "Keep it to 1-4 sentences."
)


def answer(query: str) -> tuple[str, list[str]]:
    """Retrieve + generate a grounded answer. Returns (answer_text, sources)."""
    ranked = retrieve(query)
    best_sim = ranked[0][1] if ranked else 0.0
    if not ranked or best_sim < config.RAG_MIN_SIMILARITY:
        return config.FALLBACK_MESSAGE, []

    context_parts, sources = [], []
    for chunk, sim in ranked:
        if sim <= 0:
            continue
        context_parts.append(f"[{chunk.doc}] {chunk.text}")
        if chunk.doc not in sources:
            sources.append(chunk.doc)

    context = "\n\n".join(context_parts)
    user = f"QUESTION: {query}\nCONTEXT:\n{context}"
    # Smaller token budget = faster generation (helps the <2s target). Support
    # answers are short by design, so 180 tokens is ample.
    text = llm.complete(system=_ANSWER_SYSTEM, user=user, task="rag_answer",
                        temperature=0.1, max_tokens=180)
    return text, sources
