# Domain Research: exams-deadlines

> Phase 0 deliverable per PLAN.md Section 13. Fill in before writing any
> ingestion code for this domain.

## Source

- URL(s):
  - `memphis.edu/registrar/calendars/academic/ay2526.php` — AY 2025-2026 key dates (semester start/end, breaks, final exam windows)
  - `memphis.edu/registrar/calendars/` — index of academic year calendars
  - `memphis.edu/registrar/calendars/dates/25u-dates.php` (and equivalent per-term pages) — granular per-semester registration/add-drop/withdrawal deadlines, not yet fully fetched
  - `memphis.edu/usbs/calendars/` — payment-specific deadlines (overlaps with Fees — see below)
- Format: HTML, dated lists.
- Approximate size: small per page, split across an AY-overview page plus separate per-term "dates and deadlines" pages.
- Update frequency: fast — one of `PLAN.md` §7's fast-changing domains; a full new date set publishes every academic year and every term.

## Real questions this domain should answer

1. When does Fall 2025 registration open?
2. When is Fall Break?
3. What are the final exam dates for Spring 2026?
4. When is the last day to add/drop a class this semester? *(not resolved from the AY overview page — see complications)*
5. When is MLK holiday / other breaks this academic year?

## Data complications

- **The AY overview page does not contain add/drop or withdrawal deadlines** — confirmed by fetching it directly. Those live on separate per-term "Dates & Deadlines" pages. Ingestion must pull *both* the AY overview *and* each term's dedicated dates page — treating the AY page as complete would silently drop the deadlines students actually ask about most.
- **Overlaps with Fees**: `usbs/calendars/` covers payment-specific deadlines (installment due dates, late fee cutoffs) that are also calendar-adjacent. Decide in Phase 1 which collection owns these — recommend Fees owns payment deadlines, this domain owns academic (registration/add-drop/exam) deadlines, to avoid duplicating the same dates in two collections.
- Final exam *date windows* were found (e.g. "December 5-11, 2025"), but individual **course-specific exam times/rooms** were not — those are published separately, likely closer to Course Catalog or a dedicated exam-schedule matrix. Don't assume this domain can answer "when is my specific course's final."

## Proposed retrieval strategy

- [ ] Semantic RAG
- [x] Structured lookup
- [ ] Hybrid

Justification: Matches `PLAN.md` §6. Every fact is a labeled date (event name → date/range) — small, low-cardinality, exact-match lookup ("when is X"), which favors structured/keyword retrieval over semantic embedding.
