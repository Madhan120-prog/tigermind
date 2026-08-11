# TigerMind

A LangGraph-based multi-agent assistant answering University of Memphis
student questions — housing, fees, faculty, flyers, events, exams/deadlines,
student employment, course catalog, and majors advising — using real,
publicly available university data. Phase 6 adds an SSO-gated tier (mocked
SIS) so students can look up their classes, drop/add with a human-in-the-
loop confirmation step, and check their bursar balance.

Built primarily as a portfolio project for software/AI engineering roles —
see `PLAN.md` Section 16 for how it's meant to read in an interview — and
secondarily as a second, framework-based data point on multi-agent
orchestration, alongside the hand-rolled Integrated Patient System project.

## Status

Pre-implementation. Repo scaffolding and planning docs only — see `PLAN.md`
Phase 0 for the current step.

## Architecture at a glance

Ten domains, three tiers, not ten bespoke agents:

- **Tier 1 — one generic, config-driven retrieval agent** for the eight
  simple public-info domains (Housing, Fees, Faculty, Flyers, Events,
  Exams/Deadlines, Student Employment, Course Catalog). Adding a domain
  means running ingestion + adding one config entry, not writing new agent
  code.
- **Tier 2 — Majors advising**, a stateful multi-turn intake/recommendation
  flow (declare vs. apply, GPA/prereq eligibility) — the one public-info
  domain that actually needs LangGraph's state + checkpointer.
- **Tier 3 — SIS actions** (Phase 6, SSO-gated): my classes, drop/add,
  bursar balance, against a mocked SIS. The one place the agent *takes an
  action* instead of *answering a question*, gated by `interrupt()` for
  human confirmation before anything irreversible.

Full rationale, domain table, and phased build plan: `PLAN.md`.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | FastAPI |
| Orchestration | LangGraph (StateGraph, conditional edges, checkpointer, `interrupt()`) |
| LLM | Anthropic Claude API, tiered by agent role (Haiku/Sonnet/Opus) |
| Vector store | Chroma, domain-scoped collections |
| Embeddings | Local `sentence-transformers` |
| Mock SIS (Phase 6) | FastAPI + SQLite + JWT auth |
| Frontend | React (reused chat component from the patient-system project) |
| Reproducibility | Docker Compose, pinned deps, GitHub Actions eval gate |

Full reasoning for each choice — and the alternatives considered — lives in
`CLAUDE.md`.

## Folder structure

```
tigermind/
├── .claude/
│   ├── agents/            # Subagent definitions (isolated context, own model)
│   ├── rules/              # Always-loaded conventions (architecture, git, guardrails)
│   └── skills/              # On-demand procedures (e.g. domain ingestion)
├── backend/
│   ├── app/
│   │   ├── agents/          # generic domain agent, majors agent, sis action agent
│   │   ├── config/           # domains.yaml — the Tier-1 domain registry
│   │   ├── graph/             # Router, synthesizer, guardrails, LangGraph state
│   │   ├── ingestion/          # Scrape -> chunk -> embed pipeline, per domain
│   │   ├── retrieval/           # Chroma client, structured lookup helpers
│   │   ├── mock_sis/             # Phase 6: mock SSO/SIS/bursar FastAPI service
│   │   └── main.py                 # FastAPI entrypoint
│   ├── data/
│   │   ├── raw/                    # Scraped source pages (gitignored)
│   │   └── chroma/                  # Vector store persistence (gitignored)
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/                          # Reused React chat component
├── eval/
│   ├── eval_set.csv                    # Question/domain/expected-answer pairs
│   └── run_eval.py
├── docs/
│   └── domain-research/                 # Phase 0 reconnaissance per domain
├── docker-compose.yml                     # backend + chroma + mock SIS, reproducible env
├── PLAN.md                                 # Full build plan, phases, checkpoints
└── CLAUDE.md                                # Claude Code project context (parent file)
```

## Setup

Not yet implemented — see `PLAN.md` Phase 0 and Phase 1 for what comes
first.

## Git workflow

See `.claude/rules/git-workflow.md` for branch naming, commit conventions,
and the PR/merge flow used on this project.
