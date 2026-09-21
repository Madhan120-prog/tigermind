"""Ingest one Tier-1 domain: fetch its configured sources, chunk, embed, store.

Usage: python -m app.ingestion.run housing
"""
import sys
from datetime import datetime, timezone

from app.config.loader import get_domain
from app.ingestion.chunk import MIN_CHUNK_CHARS, chunk_text
from app.ingestion.discover import discover_sources, record_key_for
from app.ingestion.fetch import fetch_page
from app.ingestion.pdf_extract import fetch_pdf
from app.retrieval.chroma_client import get_chroma_client, upsert_chunks


def _fetch(url: str) -> tuple[str, list[tuple[str, bool, str]]]:
    """Dispatch by file type, not by domain -- a domain mixing HTML policy
    pages with a PDF fee schedule (Fees) works the same way any future
    domain with the same mix would, no domain-name branch involved."""
    return fetch_pdf(url) if url.lower().endswith(".pdf") else fetch_page(url)


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
        heading, blocks = _fetch(url)
        # A block with its own record_key (a PDF row keyed by credit hours)
        # keeps it; a page-level key (a faculty member's slug) applies to
        # every block that didn't already claim a more specific one.
        page_record_key = record_key_for(url, config.source_discovery)
        chunks: list[tuple[str, str]] = []
        for text, is_atomic, block_record_key in blocks:
            key = block_record_key or page_record_key
            texts = [text] if is_atomic else chunk_text(text)
            chunks.extend((t, key) for t in texts)
        chunks = [(t, k) for t, k in chunks if len(t) >= MIN_CHUNK_CHARS]
        print(f"  {url.split('memphis.edu')[-1]} -> {len(chunks)} chunks")

        for chunk, record_key in chunks:
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

    # Chroma rejects a batch containing two identical ids outright, and
    # chunk_id is a hash of (source_url, text) -- so two chunks on the same
    # page reducing to the same text (a repeated layout-table note, e.g.)
    # crash the whole run, not just one of the two. The per-domain rebuild
    # above only guards against stale chunks *across* runs; this guards
    # against a duplicate within the very batch being built right now.
    seen: set[tuple[str, str]] = set()
    deduped = []
    for chunk in all_chunks:
        key = (chunk["source_url"], chunk["text"])
        if key not in seen:
            seen.add(key)
            deduped.append(chunk)
    if len(deduped) != len(all_chunks):
        print(f"  dropped {len(all_chunks) - len(deduped)} duplicate chunk(s)")

    upsert_chunks(config.collection, deduped)
    print(f"Ingested {len(deduped)} chunks into '{config.collection}' collection")
    return len(deduped)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m app.ingestion.run <domain>")
        sys.exit(1)
    ingest_domain(sys.argv[1])
