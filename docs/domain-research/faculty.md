# Domain Research: faculty

> Phase 0 deliverable per PLAN.md Section 13. Fill in before writing any
> ingestion code for this domain.

## Source

- URL(s):
  - No single central directory. Each department publishes its own page; pattern varies:
    - `memphis.edu/{dept}/faculty_research/faculty-directory.php` (Economics, Finance, Accountancy, Management, MIS, Supply Chain Management)
    - `memphis.edu/{dept}/faculty/` (Mechanical Engineering)
  - `memphis.edu/aa/directory/` — Academic Affairs directory, but that's administrative leadership (deans/provosts), not teaching faculty
  - `memphis.edu/fac_staff/` — general faculty/staff portal, not a searchable people directory
- Format: HTML, card/list-style per faculty member — photo, name, title, email, phone, office, sometimes research interests + Google Scholar link (confirmed via Mechanical Engineering's directory).
- Approximate size: ~20-40 departments × ~10-30 faculty each — the largest corpus by entry count of the 8 Tier-1 domains, even though each individual entry is short.
- Update frequency: slow — rosters change per semester/year, but page structure is stable.

## Real questions this domain should answer

1. Who teaches [course/subject] in the [department] department?
2. What's [professor]'s office location or email?
3. Which faculty in [department] work on [research area]?
4. Is [professor] still at the University of Memphis (active vs. emeritus)?
5. Who is the department chair for [department]?

## Data complications

- **No central directory** — the single biggest complication in this domain. Ingestion must enumerate departments individually and scrape each one's directory page separately; there's no one URL pattern covering all departments.
- Emeritus/retired faculty and current faculty are sometimes listed on the same page (confirmed on Mechanical Engineering's page, which lists Faculty, Post Doctoral Fellow, Emeritus Faculty, and Staff together) — a chunk needs to carry that status so the agent doesn't present a retired professor as actively teaching.
- **Office hours were not found on any directory page checked** — likely published per-syllabus, not centrally. "What are professor X's office hours" may not be answerable from this domain's source at all; this should be a confidence-gate case, not a guess.
- Contact info (email/phone/office) is exactly the kind of fact where an error is worse than a vague answer — reinforces the guardrails citation requirement for this domain specifically.

## Proposed retrieval strategy

- [ ] Semantic RAG
- [x] Structured lookup
- [ ] Hybrid

Justification: Matches `PLAN.md` §6. Each entry is a small set of fixed fields (name, title, email, office, department) — closer to a lookup table than prose, so keyword/exact-match retrieval on name/department should outperform semantic search for "who is X" / "who teaches in Y department" queries.
