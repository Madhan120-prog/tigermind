"""Ingest one Tier-1 domain: fetch its configured sources, chunk, embed, store.

Usage: python -m app.ingestion.run housing
"""
import sys
from datetime import datetime, timezone

from app.config.loader import get_domain
from app.ingestion.chunk import MIN_CHUNK_CHARS, chunk_text
from app.ingestion.fetch import fetch_page_blocks
from app.retrieval.chroma_client import get_chroma_client, upsert_chunks


def ingest_domain(domain_name: str) -> int:
    config = get_domain(domain_name)
    now = datetime.now(timezone.utc).isoformat()

    # Rebuild the collection from scratch each run rather than diffing --
    # chunk boundaries can change between ingestion runs (e.g. a chunker
    # fix), and at this corpus size a full rebuild is simpler and safer
    # than reconciling stale chunks left behind by a changed boundary.
    try:
        get_chroma_client().delete_collection(name=config.collection)
    except Exception:
        pass  # collection didn't exist yet -- nothing to clear

    all_chunks = []
    for url in config.sources:
        print(f"  fetching {url}")
        blocks = fetch_page_blocks(url)
        chunks = []
        for text, is_atomic in blocks:
            chunks.extend([text] if is_atomic else chunk_text(text))
        chunks = [c for c in chunks if len(c) >= MIN_CHUNK_CHARS]
        print(f"    -> {len(chunks)} chunks")
        for chunk in chunks:
            all_chunks.append(
                {
                    "text": chunk,
                    "source_url": url,
                    "freshness_tier": config.freshness_tier,
                    "last_updated": now,
                }
            )

    upsert_chunks(config.collection, all_chunks)
    print(f"Ingested {len(all_chunks)} chunks into '{config.collection}' collection")
    return len(all_chunks)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m app.ingestion.run <domain>")
        sys.exit(1)
    ingest_domain(sys.argv[1])
