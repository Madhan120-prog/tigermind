# Domain Research: student-employment

> Phase 0 deliverable per PLAN.md Section 13. Fill in before writing any
> ingestion code for this domain.

## Source

- URL(s):
  - `memphis.edu/studentemployment/` — main hub
  - `memphis.edu/studentemployment/faq_students.php` — eligibility, application process, pay, hours, FWS vs. RSE
  - `memphis.edu/scholarships/student_employment/sejobs.php`, `.../sepay.php` — Federal Work-Study specifics, pay ranges
  - `memphis.edu/iss/current_international_students/employment_on_campus.php` — international-student-specific on-campus rules
- Format: HTML, FAQ-style prose.
- Approximate size: small-to-medium, a handful of pages.
- Update frequency: mixed — eligibility rules/process are slow-changing; pay rates are fast-changing. Actual open positions are posted on TigerLink/Handshake, an external platform outside this project's scrape scope.

## Real questions this domain should answer

1. Am I eligible to work an on-campus job as a part-time student?
2. What's the difference between Federal Work-Study and Regular Student Employment?
3. How many hours a week can I work during the semester?
4. Where do I actually find and apply for open positions?
5. What's the current student employee minimum wage?

## Data complications

- **The pay-rate figure found is explicitly dated to Spring 2022** ("minimum wage for student employees is $9.00 per hour," with a planned increase to $10.00 in Fall 2022) — years stale as of today. This is a concrete, confirmed example of `PLAN.md` §7's freshness concern: the page doesn't self-update, and citing this number without flagging it as unverified-current would be a fabrication risk. Needs re-verification at ingestion time regardless of Student Employment's otherwise-slow-changing classification.
- **Actual job postings live outside this domain's source entirely** — on TigerLink (Handshake), a third-party platform not scraped by this project. This domain can answer "how do I find a job" (process) but not "what jobs are open right now" — the agent should say so rather than imply live listings it doesn't have.
- International students have a stricter, separate hour-limit rule (20 hrs/week regular vs. 25 for domestic) — a chunk stating "up to 25 hours" without that caveat would be wrong for a meaningful part of the audience.
- FWS and RSE are mutually exclusive per student — worth preserving as an explicit fact rather than losing it inside generic "employment options" prose.

## Proposed retrieval strategy

- [x] Semantic RAG
- [ ] Structured lookup
- [ ] Hybrid

Justification: Matches `PLAN.md` §6. FAQ-style prose; the few numeric facts (hour limits, pay rate) are low-cardinality enough to embed within their explanatory context rather than needing structured lookup.
