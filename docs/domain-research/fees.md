# Domain Research: fees

> Phase 0 deliverable per PLAN.md Section 13. Fill in before writing any
> ingestion code for this domain.

## Source

- URL(s):
  - `memphis.edu/usbs/fees/` — fee category overview, tuition estimator pointer
  - `memphis.edu/usbs/fees/otherfees.php` — itemized fee list (TNeCampus, UofM Global, course fees, application fees, late fees)
  - `memphis.edu/usbs/fees/2526fees/ug_resident.pdf` — actual dollar-amount fee schedule (PDF, per year/residency/level)
  - `memphis.edu/usbs/calendars/` — payment deadlines
  - `memphis.edu/financialaid/coa.php` — broader cost-of-attendance estimate (housing/food included)
- Format: Mixed — HTML overview/explanation pages, but the actual dollar amounts live in per-year, per-residency, per-level **PDF** fee schedules.
- Approximate size: several HTML pages + a matrix of PDFs (resident/non-resident/international × undergrad/grad/law × standard/UofM Global/TNeCampus).
- Update frequency: annual — current cycle is "2526fees" (2025-26) in the URL path.

## Real questions this domain should answer

1. How much does a resident undergraduate pay per credit hour this year?
2. What's the difference in cost between UofM Global and standard on-campus tuition?
3. What is the late payment fee if I don't pay by the first day of classes?
4. What are the installment payment plan due dates for fall?
5. How much is the mandatory Tiger Eat$ dining charge?
6. What does the University Service Fee cover?
7. How much is the application fee for international undergraduates?

## Data complications

- The actual dollar amounts live in per-year/residency/level **PDF** schedules (e.g. `2526fees/ug_resident.pdf`), not the HTML pages — ingestion needs a PDF text extractor, confirming what `PLAN.md`'s earlier draft flagged.
- Multiple parallel tuition tracks exist at the same course level — standard campus, "UofM Global" (Mxx sections), "TNeCampus" (Rxx sections) — each with a materially different per-credit-hour rate. A chunk stating a rate without naming its track is misleading.
- Course-specific fees (music, engineering, nursing, business, fine arts) are a long tail of small add-ons layered on base tuition — worth its own structured chunk list rather than folding into general fee prose.
- Institutional pages can go stale for years without anyone noticing (see Student Employment's 2022-dated wage figure) — cross-check any dollar figure against the current-year PDF, don't trust an older HTML page's inline number at face value.

## Proposed retrieval strategy

- [x] Semantic RAG
- [ ] Structured lookup
- [ ] Hybrid

Justification: Matches `PLAN.md` §6. Fee *policy* content (what a fee covers, payment plan mechanics) is prose-appropriate for semantic search; the itemized dollar amounts are a bounded, low-cardinality list that can be embedded as short structured-text chunks without needing true regex/structured lookup.
