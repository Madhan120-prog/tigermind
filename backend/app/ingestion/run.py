"""Ingest one Tier-1 domain: fetch its configured sources, chunk, embed, store.

Usage: python -m app.ingestion.run housing
"""
import sys
from datetime import datetime, timezone

from app.config.loader import get_domain
from app.ingestion.chunk import MIN_CHUNK_CHARS, chunk_text
from app.ingestion.discover import discover_sources, record_key_for
from app.ingestion.fetch import fetch_page
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

    if config.source_discovery:
        sources = discover_sources(config.source_discovery)
        print(f"  discovered {len(sources)} sources from the sitemap")
    else:
        # No sitemap entry to read a real change date from, so fall back to
        # the fetch time and accept that it overstates freshness.
        sources = [(url, now) for url in config.sources]

    all_chunks = []
    for url, last_updated in sources:
        heading, blocks = fetch_page(url)
        chunks = []
        for text, is_atomic in blocks:
            chunks.extend([text] if is_atomic else chunk_text(text))
        chunks = [c for c in chunks if len(c) >= MIN_CHUNK_CHARS]
        print(f"  {url.split('memphis.edu')[-1]} -> {len(chunks)} chunks")

        record_key = record_key_for(url, config.source_discovery)
        for chunk in chunks:
            all_chunks.append(
                {
                    # The heading rides on every chunk: a chunk taken from the
                    # middle of a page has lost what the page was about.
                    "text": f"{heading}\n{chunk}" if heading else chunk,
                    "source_url": url,
                    "freshness_tier": config.freshness_tier,
                    "last_updated": last_updated or now,
                    "record_key": record_key,
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
