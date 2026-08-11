# Architecture Rules

Full rationale and diagram: `PLAN.md` Sections 3-5. This file is the quick
reference while implementing.

## Three tiers — don't blur them

- **Tier 1 (generic agent)**: Housing, Fees, Faculty, Flyers, Events,
  Exams/Deadlines, Student Employment, Course Catalog. One function:
  `generic_domain_agent(state, domain: str)`. Behavior differs only via
  `backend/app/config/domains.yaml` (collection name, retrieval mode,
  prompt snippet, freshness tier). If you find yourself adding an
  `if domain == "housing":` branch inside this function, stop — that
  logic belongs in the config, or the domain doesn't belong in Tier 1.
- **Tier 2 (Majors)**: stateful intake (`interests`, `gpa`,
  `completed_courses` held via checkpointer across turns), ending in an
  `interrupt()`-gated declare-vs-apply recommendation. Static "what majors
  exist / what does X major cover" questions are Tier 1 (`programs`
  collection) — route them there, not into the stateful flow.
- **Tier 3 (SIS actions, Phase 6)**: the only tier that writes. Every
  write (drop/add) is: propose → `interrupt()` → student confirms →
  execute against mock SIS. Never execute a write without that pause.

## Router / synthesizer / guardrails

- Router classifies intent → a list of active Tier-1/2 domains, or a
  Tier-3 action intent. Tier-3 requests short-circuit to an auth check
  before anything else.
- Synthesizer fires only when the router's active-domain list has more
  than one entry — don't run it on every request.
- Guardrails run on every path, including Tier-3, before the response
  returns: citation check, confidence gate, freshness disclaimer (see
  `guardrails.md`), deferrals.

## Retrieval mode per domain

- Structured (keyword/regex before embeddings): course codes, faculty
  names, exam dates.
- Semantic: prose-heavy domains — Housing, Fees, Flyers, Events, Student
  Employment, Majors process text.
- Hybrid: Course Catalog only (course-code queries → structured; "how do
  I withdraw" → semantic).
