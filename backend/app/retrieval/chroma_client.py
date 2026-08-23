import hashlib
import os
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
    """chunks: list of {"text", "source_url", "freshness_tier", "last_updated"}."""
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
            }
            for c in chunks
        ],
    )


def query_domain(domain: str, question: str, k: int = 4) -> list[dict]:
    collection = get_collection(domain)
    results = collection.query(query_texts=[question], n_results=k)

    hits = []
    for text, metadata, distance in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        hits.append({"text": text, "metadata": metadata, "distance": distance})
    return hits
