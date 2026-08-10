# CLAUDE.md — TigerGuide

## Project
LangGraph-based multi-agent assistant answering University of Memphis
student questions (housing, fees, registration, majors, faculty, campus
employment).

Full context, domain scope, and the phased build plan live in `PLAN.md` —
read the relevant phase section there before starting work.

## Working agreement
- Build phase by phase per `PLAN.md` Section 8. Don't get ahead of the
  current phase.
- At the end of each phase, run the eval subset from `eval/eval_set.csv`
  before moving on.
- Checkpoint rule: if the vertical slice pipeline isn't proven by the end
  of Phase 2, cut scope per `PLAN.md` Section 8 rather than pushing forward
  on all domains at once.
- Follow `.claude/rules/git-workflow.md` for branching, commits, and PRs —
  one branch per phase, conventional commit messages, no direct pushes to
  `main`.

## Stack
- **Backend: FastAPI** — async-native (matters for concurrent LLM/retrieval
  calls), built-in Pydantic validation, auto-generated docs. Chosen over
  Flask (no native async, more manual wiring) and Django (batteries-included
  ORM/admin is unused weight for an API with no relational data model).
- **Orchestration: LangGraph** — explicit state graph with conditional
  edges, checkpointing, and human-in-the-loop interrupts, which is exactly
  what the Majors intake flow needs. Chosen over CrewAI (role-based,
  less control over exact state transitions) and AutoGen (conversation-driven,
  less deterministic output structure) — this project's stated purpose
  requires the explicit state/checkpoint primitives specifically.
- **Vector store: Chroma** — local, zero-infra, ergonomic metadata
  filtering (used for the `domain` filter, same pattern as the patient
  system's `patient_id` filter). Chosen over Pinecone/Weaviate (managed
  infra unnecessary at this corpus size) and pgvector (no relational data
  need to justify a Postgres dependency).
- **Embeddings: local `sentence-transformers`** — free, offline, no
  per-token cost or rate limits. Sufficient quality for this corpus size;
  an API-based embedding model (OpenAI/Cohere/Voyage) adds cost and an
  external dependency with no clear quality need here.
- **Frontend: React** — reuses the existing chat component from the
  Integrated Patient System project. Chosen over Streamlit (faster to
  prototype but reads as a data-science demo, not a reusable component) and
  Next.js (SSR/routing overhead not needed for a single-page chat UI).

## Skills
- `.claude/skills/ingest-domain/` — the scrape → chunk → embed → verify
  pipeline for bringing a domain online. Invoke when starting a new
  domain's ingestion rather than re-deriving the steps.

## Commands
_(fill in once the FastAPI skeleton exists — e.g. `uvicorn app.main:app --reload`, `pytest`)_

## Maintenance
Keep this file under ~150 lines. New detail goes in `.claude/rules/`, not here.

## Compact instructions
When compacting, always preserve: which PLAN.md phase is in progress, the
most recent eval subset results (pass/fail per domain), which git branch is
active, and any files modified but not yet verified. Drop exploratory
reasoning and superseded approaches.
