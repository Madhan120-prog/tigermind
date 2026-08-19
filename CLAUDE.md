# CLAUDE.md — TigerMind

## Project
LangGraph-based multi-agent assistant answering University of Memphis
student questions across ten domains (housing, fees, faculty, flyers,
events, exams/deadlines, student employment, course catalog, majors
advising, and Phase-6 SSO-gated SIS actions). Primary goal: a portfolio
piece for software/AI engineering roles — see `PLAN.md` Section 16.

Full context, domain scope, and the phased build plan live in `PLAN.md` —
read the relevant phase section there before starting work.

## Working agreement
- Build phase by phase per `PLAN.md` Section 13. Don't get ahead of the
  current phase.
- At the end of each phase, run the eval subset from `eval/eval_set.csv`
  before moving on.
- Checkpoint rule: if the vertical slice pipeline isn't proven by the end
  of Phase 2, cut scope per `PLAN.md` Section 13 rather than pushing
  forward on all domains at once.
- **One generic agent, not one per domain.** All eight Tier-1 domains
  (`PLAN.md` Section 3) share a single config-driven agent. Adding a
  domain means an ingestion run + one entry in
  `backend/app/config/domains.yaml` — never a new agent function. If a
  "specialist" needs domain-specific branching logic, that's a signal it
  belongs in Tier 2/3, not Tier 1.
- Phase 6 (SSO/SIS) is a **mocked** service — there is no real UofM SIS
  integration available. Never let docs, code comments, or the README
  imply a live institutional connection.
- Follow `.claude/rules/git-workflow.md` for branching, commits, and PRs —
  one branch per phase, conventional commit messages, no direct pushes to
  `main`. Commits are authored solely by the user — no AI co-author
  trailer, ever, in this repo. The user is the only collaborator and
  performs every merge themselves — Claude Code opens PRs, never merges
  them.
- **No hardcoding, minimize dependencies.** See `PLAN.md` Section 10 and
  `.claude/rules/architecture.md` — domain differences belong in
  `backend/app/config/domains.yaml`, not code branches; don't add a
  package that overlaps with something already in the stack.
- **After every commit, explain what changed in plain language.** The
  user is learning this stack as the project goes and is not yet
  proficient in it — skip jargon-dense summaries, explain what the change
  does and why in terms a newer engineer can follow.

## Stack
- **Backend: FastAPI** — async-native (matters for concurrent LLM/retrieval
  calls), built-in Pydantic validation, auto-generated docs. Chosen over
  Flask (no native async) and Django (unused ORM/admin weight).
- **Orchestration: LangGraph** — explicit state graph, conditional edges,
  checkpointing, and `interrupt()` for human-in-the-loop gates — required
  by both the Majors intake flow and the Phase 6 drop/add action, not
  optional stretch goals. Chosen over CrewAI (less control over exact
  state transitions) and AutoGen (less deterministic output structure).
- **LLM: Anthropic Claude API**, tiered per agent role — Haiku for
  mechanical ingestion/guardrails, Sonnet for retrieval/synthesis/majors,
  Opus for the router's judgment call. Cost-tiered by how much judgment
  the node actually needs.
- **Vector store: Chroma** — local, zero-infra, ergonomic `domain`
  metadata filtering. Chosen over Pinecone/Weaviate (managed infra
  unnecessary at this corpus size) and pgvector (no relational need).
- **Embeddings: local `sentence-transformers`** — free, offline, no
  per-token cost. Sufficient for this corpus size.
- **Mock SIS (Phase 6): FastAPI + SQLite + JWT** — simulates the SSO/SIS
  integration pattern (real auth flow, per-student authorization checks)
  against seeded fake data, since no real UofM SIS API is available.
- **Frontend: React** — reuses the existing chat component from the
  Integrated Patient System project. Chosen over Streamlit (reads as a
  data-science demo) and Next.js (SSR/routing overhead not needed here).

## Skills
- `.claude/skills/ingest-domain/` — the scrape → chunk → embed → verify
  pipeline for bringing a Tier-1 domain online. Invoke when starting a new
  domain's ingestion rather than re-deriving the steps.

## Commands
_(fill in once the FastAPI skeleton exists — e.g. `uvicorn app.main:app --reload`, `pytest`, `docker compose up`)_

## Maintenance
Keep this file under ~150 lines. New detail goes in `.claude/rules/`, not here.

## Compact instructions
When compacting, always preserve: which PLAN.md phase is in progress, the
most recent eval subset results (pass/fail per domain), which git branch is
active, and any files modified but not yet verified. Drop exploratory
reasoning and superseded approaches.
