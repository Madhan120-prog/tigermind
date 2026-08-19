# Domain Research: events

> Phase 0 deliverable per PLAN.md Section 13. Fill in before writing any
> ingestion code for this domain.

## Source

- URL(s):
  - `memphis.edu/calendar/` — general campus events calendar
  - `memphis.edu/tigerzone` — TigerZone, the Registered Student Organization (RSO) event/engagement platform
  - Department-specific calendars also exist independently (e.g. Marcus W. Orr Center for the Humanities, UM3D) — same no-central-source pattern as Faculty/Flyers
- Format: HTML, but `/calendar/` appears to be a JS-rendered interactive widget — a direct fetch in this research pass returned only page chrome (pointers to "Athletic Events" and "TigerZone"), not individual event listings. TigerZone is a full platform; browsing may be public but interacting (RSVP) likely requires login.
- Approximate size: **unresolved** — can't be estimated until ingestion tooling can actually render/query the calendar.
- Update frequency: fast — flagged in `PLAN.md` §7 alongside Flyers and Exams/Deadlines.

## Real questions this domain should answer

1. What events are happening on campus this week?
2. Are there any [category, e.g. humanities/athletics] events coming up?
3. How do I find events hosted by student organizations?
4. How do I submit my own event to the campus calendar?

## Data complications

- **Two separate systems, not one**: the general campus calendar and TigerZone (student-org events) are different platforms with different content — "what events are happening" may need to span both, which fragments this domain more than any other Tier-1 domain researched so far.
- **JS-rendering risk, confirmed**: a plain HTTP fetch of `/calendar/` did not return individual event data. This likely needs either a JSON/API feed (common for calendar widgets) or a headless-browser scrape rather than simple HTML parsing. **Needs a dedicated ingestion spike before Phase 1/2** to confirm which approach actually works — flagging now rather than discovering it mid-ingestion.
- Department-level calendars (Humanities, UM3D, etc.) add further fragmentation on top of the two main systems.

## Proposed retrieval strategy

- [x] Semantic RAG (dates as first-class metadata, not just embedded text)
- [ ] Structured lookup
- [ ] Hybrid

Justification: Matches `PLAN.md` §6's default for Events, though the *ingestion mechanism* is the open question here, not the retrieval mode. Once event data is actually extracted, chunking by individual event (title, date, time, location, category) with date-range filtering may end up mattering more than raw semantic similarity — worth revisiting as Hybrid if the JS-rendering spike turns up structured JSON.
