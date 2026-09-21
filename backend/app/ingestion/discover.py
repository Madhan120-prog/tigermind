"""Discover a domain's source URLs from the site's sitemap.

Hand-listing sources goes stale silently. Phase 0 recorded a faculty
directory URL pattern for this site that now returns 404 across every
department that once used it, and guessing replacements had roughly a one
in nine hit rate. The sitemap is the site's own list of what exists, and
its <lastmod> is a real change date rather than the moment we happened to
fetch the page.
"""
import re

import httpx

from app.ingestion.fetch import USER_AGENT

_ENTRY_PATTERN = re.compile(
    r"<url>\s*<loc>(.*?)</loc>\s*(?:<lastmod>(.*?)</lastmod>)?", re.S
)


def discover_sources(discovery: dict, timeout: float = 60.0) -> list[tuple[str, str]]:
    """Return (url, lastmod) pairs from the sitemap matching `include`."""
    response = httpx.get(
        discovery["sitemap"],
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
        follow_redirects=True,
    )
    response.raise_for_status()

    include = re.compile(discovery["include"])
    found = [
        (loc, lastmod)
        for loc, lastmod in _ENTRY_PATTERN.findall(response.text)
        if include.search(loc)
    ]

    limit = discovery.get("limit")
    return found[:limit] if limit else found


def record_key_for(url: str, discovery: dict) -> str:
    """Extract a record's structured identity from its URL.

    Taken from the URL rather than parsed out of the page: these pages are
    one-record-per-page with the identity in the slug
    (`.../faculty-directory/amini-mehdi.php`), which is deterministic and
    survives whatever the department's HTML happens to look like. Only
    populated when a domain configures `record_key_from`, so domains whose
    pages aren't records don't get a meaningless one.
    """
    pattern = discovery.get("record_key_from")
    if not pattern:
        return ""
    match = re.search(pattern, url)
    return match.group(1) if match else ""
