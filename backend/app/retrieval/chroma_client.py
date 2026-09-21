import hashlib
import os
import re
from functools import lru_cache
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

# backend/app/retrieval/chroma_client.py -> backend/
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


@lru_cache
def get_chroma_client() -> chromadb.ClientAPI:
    persist_dir = Path(os.environ.get("CHROMA_PERSIST_DIR", "./data/chroma"))
    if not persist_dir.is_absolute():
        # Anchor to backend/, not the process's cwd, so ingestion and
        # querying always land on the same store regardless of which
        # directory a command was run from.
        persist_dir = BACKEND_DIR / persist_dir
    return chromadb.PersistentClient(path=str(persist_dir))


@lru_cache
def get_embedding_function():
    # Local sentence-transformers model -- free, offline, no per-token cost.
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )


def get_collection(domain: str):
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=domain, embedding_function=get_embedding_function()
    )


def chunk_id(source_url: str, chunk_text: str) -> str:
    """Stable id from content, so re-running ingestion upserts instead of duplicating."""
    digest = hashlib.sha256(f"{source_url}::{chunk_text}".encode()).hexdigest()
    return digest[:16]


def upsert_chunks(domain: str, chunks: list[dict]) -> None:
    """chunks: {"text", "source_url", "freshness_tier", "last_updated", "record_key"}."""
    collection = get_collection(domain)
    collection.upsert(
        ids=[chunk_id(c["source_url"], c["text"]) for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[
            {
                "domain": domain,
                "source_url": c["source_url"],
                "freshness_tier": c["freshness_tier"],
                "last_updated": c["last_updated"],
                "record_key": c.get("record_key", ""),
            }
            for c in chunks
        ],
    )


def _record_keys(domain: str) -> list[str]:
    metadatas = get_collection(domain).get(include=["metadatas"])["metadatas"]
    return sorted({m.get("record_key") or "" for m in metadatas} - {""})


def _named_record(domain: str, question: str) -> str | None:
    """Find the single record a question names, or None.

    Embeddings are unreliable on rare proper nouns -- one faculty member's
    page reads much like another's, so "Dr. Amini's office" competes with
    forty near-identical colleagues. An exact token match on the record's
    identity is what "structured" means here. Deliberately no LLM call: the
    record keys are already known, so this stays deterministic.

    Returns None when several records match (a shared first name, say) --
    an ambiguous filter is worse than none, so it falls back to semantic.

    The length-3 floor on a key part exists to drop short noise words from a
    slug like "van-am" -- but it would also drop a credit-hour count like
    "9", which is exactly the token a fee schedule's rows are keyed by and
    the only thing distinguishing one row from the next. A digit is never
    noise the way a short word can be, so it skips the floor.
    """
    lowered = question.lower()
    matches = [
        key
        for key in _record_keys(domain)
        if any(
            re.search(rf"\b{re.escape(part)}\b", lowered)
            for part in key.split("-")
            if len(part) > 2 or part.isdigit()
        )
    ]
    return matches[0] if len(matches) == 1 else None


# 6, not 4: per-row table chunking put six sibling rate rows between a
# question and the prose chunk answering it. Chosen empirically against
# the housing eval, not calibrated -- see PLAN.md Section 17.9.
def query_domain(
    domain: str, question: str, k: int = 6, mode: str = "semantic"
) -> list[dict]:
    collection = get_collection(domain)

    # Dispatch on the configured retrieval mode, never on the domain name --
    # see .claude/rules/architecture.md. A new structured domain is a config
    # entry; it does not touch this function.
    #
    # "hybrid" and "structured" share this path deliberately: PLAN.md
    # Section 6 defines hybrid as "a named record resolves by exact match,
    # everything else is prose" -- which is already exactly what the
    # named-record-or-None fallback below does. A second branch that only
    # ever did the same thing would be duplication with no behavior behind
    # it, not a real distinction.
    where = None
    if mode in ("structured", "hybrid"):
        named = _named_record(domain, question)
        if named is not None:
            where = {"record_key": named}

    results = collection.query(query_texts=[question], n_results=k, where=where)

    hits = []
    for text, metadata, distance in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        hits.append({"text": text, "metadata": metadata, "distance": distance})
    return hits
