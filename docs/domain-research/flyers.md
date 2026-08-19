# Domain Research: flyers

> Phase 0 deliverable per PLAN.md Section 13. Fill in before writing any
> ingestion code for this domain.

## Source

- URL(s):
  - `memphis.edu/efiles/announcements/students.php` — main student announcements page (advising, internships, deadlines, leadership opportunities)
  - `memphis.edu/mediaroom/releases/` — official university news releases (broader than "flyers," more press/PR)
  - `memphis.edu/mediaroom/releases/newsarchive.php` — archive of past releases
  - Per-college news pages (e.g. Herff College of Engineering's "In the News") — separate from the central announcements page
- Format: HTML, prose blocks / short announcement summaries with links out to fuller detail (e.g. an advising blog).
- Approximate size: small — a handful of live announcement blocks at any time, no visible pagination.
- Update frequency: fast — one of `PLAN.md` §7's fast-changing domains, alongside Events and Exams/Deadlines.

## Real questions this domain should answer

1. What deadlines or advising info is currently posted for [college]?
2. Are there any student trustee / leadership applications open right now?
3. What are the current "items of interest" on the student announcements page?
4. Where do I find department-specific news, e.g. from Engineering?

## Data complications

- **No date stamps.** Confirmed directly: a "student trustee" announcement referenced a meeting "held on March 17" with no year given — no way to tell from the page alone whether it's current. Freshness metadata has to be *assigned by ingestion* (fetch timestamp), since the source page doesn't provide it.
- **No archival/removal signal** — nothing indicates whether stale announcements get taken down or just accumulate. Re-ingestion should fully replace the prior snapshot each run rather than assume old chunks were intentionally kept.
- This is the domain where the freshness disclaimer (`PLAN.md` §7, `guardrails.md`) needs to be most aggressive — the source doesn't self-police staleness, so the agent has to.
- College-specific news lives on separate per-college pages — same no-central-source problem as Faculty; likely needs multiple source pages, not just the one central announcements page.

## Proposed retrieval strategy

- [x] Semantic RAG
- [ ] Structured lookup
- [ ] Hybrid

Justification: Matches `PLAN.md` §6. Short prose blocks, not structured records — semantic search over recently-ingested chunks, combined with aggressive freshness disclaimers, fits better than structured lookup.
