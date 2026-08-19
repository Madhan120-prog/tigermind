# Domain Research: housing

> Phase 0 deliverable per PLAN.md Section 13. Fill in before writing any
> ingestion code for this domain.

## Source

- URL(s):
  - `memphis.edu/reslife/housing101/housingrates.php` — rates table
  - `memphis.edu/reslife/reshalls/` — hall types, capacity, amenities
  - `memphis.edu/reslife/resources/housing.php` — contract terms, cancellation fee schedule
  - `memphis.edu/reslife/about/faqs.php` — move-in/move-out, application process, eligibility
  - `memphis.edu/reslife/reshalls/gsfh.php` — graduate/family housing (not yet fetched in detail)
  - **Avoid** `classic.memphis.edu/reslife/...` — an older mirror of the same content; ingest only from `www.memphis.edu` to prevent duplicate/stale chunks.
- Format: HTML. Mostly prose (contracts, FAQs), plus one genuine rates table (hall × academic year).
- Approximate size: ~5-6 pages, short-to-medium length each. Small corpus.
- Update frequency: Rates are published multi-year in advance (a 2025-26 through 2027-28 table already exists) but the *current* semester's charges are said to post "in late July" each cycle. Cancellation fee schedule and move-in/move-out dates are semester-specific and republished each term.

## Real questions this domain should answer

1. How much does it cost to live in South Hall / [a given hall] this year?
2. What's the difference between traditional residence halls and apartment-style housing?
3. Can freshmen live in apartment-style housing (e.g. Victory Park, Carpenter Complex)?
4. What's the cancellation fee if I back out of my fall housing contract in June?
5. When do I have to move out after finals?
6. When does housing applications open, and does applying earlier matter?
7. What's included in graduate/family housing vs. a traditional hall?
8. Is there an extra fee beyond the room rate (e.g. mail services)?

## Data complications

- **Multi-year rate table**: the rates page lists 2025-26, 2026-27, and 2027-28 side by side per hall. Ingestion/chunking needs to preserve the academic-year column alongside each rate — a chunk that drops the year label becomes actively misleading, not just incomplete.
- **Date-tiered cancellation fees, split by term**: the cancellation schedule has separate Fall and Spring fee ladders (e.g. Fall's "June 1-30 → $750" vs. Spring's "January 2-15 → $1,000"). These must not get merged into one generic "cancellation fee" fact during chunking.
- **Duplicate info across pages**: the FAQ page restates "rates vary, see the rates page" rather than giving numbers — the rates page is the single source of truth; the FAQ page should be ingested for policy/process content only, not rates.
- **Unresolved**: no page found yet that states outright whether on-campus housing is *required* for freshmen (only that specific halls are earmarked for them). Don't let ingestion or the agent assert a mandatory-housing policy that isn't actually stated — flag this as a confidence-gate case if a student asks it directly, or find the authoritative page (likely Admissions/First-Year Experience, not Residence Life) before Phase 1.
- **Semester-specific dates go stale fast**: e.g. "Fall 2026 move-out deadline is May 8 by noon" is only true for one semester. This is a slow-changing domain overall, but this specific fact behaves like a fast-changing one — tag it accordingly rather than assuming Housing's whole freshness tier applies uniformly.

## Proposed retrieval strategy

- [x] Semantic RAG
- [ ] Structured lookup
- [ ] Hybrid

Justification: Confirms `PLAN.md` §6's classification. Almost everything here is prose (policies, FAQs, hall descriptions); even the rates table is small and low-cardinality enough (5 traditional halls × 3 years, a handful of apartment complexes) to chunk as short structured-text blocks keyed by hall name rather than needing true regex/structured lookup like course codes or exam dates. Semantic retrieval over well-chunked, hall-scoped text handles all 8 sample questions above.
