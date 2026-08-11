# Guardrails Rules

Applies to the `guardrails` node — runs on every response path (Tier 1,
Tier 2, and Tier 3), always last before returning to the student.

## Citation requirement

Every factual claim sourced from retrieval must carry a source link/name
in the response. No bare assertions about fees, dates, policies, or
eligibility without a citation back to the ingested chunk's source.

## Freshness disclaimer — two tiers, not one

Per `PLAN.md` Section 7:

- **Fast-changing** (Flyers, Events, Exams/Deadlines): append a "confirm
  this is still current" note aggressively — these domains have a short
  re-ingestion TTL and are the most likely to be stale.
- **Slow-changing** (Housing, Fees, Faculty, Programs): append the same
  disclaimer whenever the answer cites a specific dollar amount or date,
  since those are the fields most likely to change semester-to-semester
  even if the rest of the page is stable.

## Deferral pattern

Defer to an official human/office rather than answering directly when:

- The question requires legal/visa/immigration judgment (international
  student employment eligibility, etc.) — defer to International
  Programs.
- The question is about the student's *individual* financial aid award
  or bursar dispute (not general fee schedules) — defer to the Bursar's
  office, unless it's a Tier-3 balance lookup the mock SIS can actually
  answer.
- The question asks the agent to guarantee a registration or major
  outcome ("will I get into X major") — state eligibility criteria from
  retrieval, but don't promise an admission decision.

## Confidence gate

If retrieval returns low-relevance results (below the similarity
threshold set in `backend/app/retrieval/`), say so explicitly rather than
answering from a weak match — "I couldn't find a confident answer to that
in [domain]'s current data" beats a fabricated-sounding response.
