# TigerMind

A LangGraph-based multi-agent assistant answering University of Memphis
student questions — housing, fees, faculty, student employment, and majors
advising are live today, using real, publicly available university data.
Flyers, Events, Exams/Deadlines, and Course Catalog were researched but
not built (see `PLAN.md` 17.5/17.12 — two are blocked by bot-detection or
JS-rendering, two were deferred as adding no new retrieval capability).
Phase 6 (not yet built) will add an SSO-gated tier (mocked SIS) so
students can look up their classes, drop/add with a human-in-the-loop
confirmation step, and check their bursar balance.

Built primarily as a portfolio project for software/AI engineering roles —
see `PLAN.md` Section 16 for how it's meant to read in an interview — and
secondarily as a second, framework-based data point on multi-agent
orchestration, alongside the hand-rolled Integrated Patient System project.

## Status

Phases 0-5 are merged to `main`: all 5 live domains, the stateful Majors
advising agent, a real router/synthesizer/guardrails graph behind one
`/ask` endpoint, and a CI eval gate (`.github/workflows/eval.yml`) that
re-ingests real data and blocks a merge on a failing question. This is
the "portfolio-ready checkpoint" per `PLAN.md` §13 — demo-able and
resume-worthy on its own. Phase 6 (mocked SSO/SIS actions) is the one
remaining phase, explicitly optional. See `PLAN.md` §13 for the full
phase-by-phase history and `docs/knowledge-base.md` for what was actually
learned building each one.

## Architecture at a glance

A router decides where a question goes, not the caller — not ten bespoke
agents per domain:

- **Tier 1 — one generic, config-driven retrieval agent**, live for
  Housing, Fees, Faculty, Student Employment, and Programs (what
  majors/programs exist). Adding a domain means running ingestion +
  adding one `domains.yaml` entry, not writing new agent code. Flyers,
  Events, Exams/Deadlines, and Course Catalog were researched (Phase 0)
  but never built — see `PLAN.md` 17.5/17.12.
- **Tier 2 — Majors advising**, a stateful multi-turn intake/recommendation
  flow (declare vs. apply, GPA/prereq eligibility against a real,
  verified Nursing ruleset) — the one domain that actually needs
  LangGraph's state + checkpointer + `interrupt()`.
- **Tier 3 — SIS actions** (Phase 6, not yet built, SSO-gated): my classes,
  drop/add, bursar balance, against a mocked SIS. The one place the agent
  will *take an action* instead of *answering a question*, gated by
  `interrupt()` for human confirmation before anything irreversible.

One router (`backend/app/agents/router.py`) classifies every question —
Tier-1 (one or more domains, fanned out and synthesized if more than one),
Majors, or out of scope — behind a single `/ask` endpoint. Full rationale,
domain table, and phased build plan: `PLAN.md`.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | FastAPI |
| Orchestration | LangGraph (StateGraph, conditional edges, checkpointer, `interrupt()`) |
| LLM | Anthropic Claude API, tiered by agent role (Haiku/Sonnet/Opus) |
| Vector store | Chroma, domain-scoped collections |
| Embeddings | Local `sentence-transformers` |
| Mock SIS (Phase 6) | FastAPI + SQLite + JWT auth — not yet built |
| Frontend | Deferred, not built — see `PLAN.md` 17.8 |
| Reproducibility | Pinned deps, GitHub Actions eval gate (`.github/workflows/eval.yml`). Docker Compose deferred, not built — see `PLAN.md` 17.8 |

Full reasoning for each choice — and the alternatives considered — lives in
`CLAUDE.md`.

## Folder structure

```
tigermind/
├── .github/
│   └── workflows/
│       └── eval.yml                  # CI: fresh ingestion + all 3 eval gates on every PR
├── .claude/
│   ├── agents/            # Subagent definitions (isolated context, own model)
│   ├── rules/              # Always-loaded conventions (architecture, git, guardrails)
│   └── skills/              # On-demand procedures (e.g. domain ingestion)
├── backend/
│   ├── app/
│   │   ├── agents/          # generic domain agent, router, synthesizer, majors intake/recommend
│   │   ├── config/           # domains.yaml — the Tier-1 domain registry
│   │   ├── graph/             # build_app.py (the one router-driven graph), guardrails, app state
│   │   ├── ingestion/          # Scrape -> chunk -> embed pipeline, per domain
│   │   ├── retrieval/           # Chroma client, structured lookup helpers
│   │   └── main.py                 # FastAPI entrypoint -- one POST /ask
│   ├── data/
│   │   ├── raw/                    # Scraped source pages (gitignored)
│   │   └── chroma/                  # Vector store persistence (gitignored)
│   ├── tests/                        # Reserved, unused -- a different kind of test than eval/, see PLAN.md 17.7
│   ├── requirements.txt
│   └── .env.example
├── frontend/                          # Empty placeholder -- deferred, see PLAN.md 17.8
├── eval/
│   ├── eval_set.csv                    # Tier-1 question/domain/expected-answer pairs
│   ├── majors_scenarios.py              # Multi-turn Majors conversation scenarios
│   ├── router_scenarios.py               # Router/synthesis scenarios
│   ├── judge.py                           # LLM-as-judge grading, shared by the runners
│   ├── run_eval.py                         # python -m eval.run_eval --all --gate
│   ├── run_majors_eval.py                   # python -m eval.run_majors_eval --gate
│   └── run_router_eval.py                    # python -m eval.run_router_eval --gate
├── docs/
│   ├── domain-research/                 # Phase 0 reconnaissance per domain
│   └── knowledge-base.md                 # Phase-by-phase study/interview notes
├── PLAN.md                                 # Full build plan, phases, checkpoints
└── CLAUDE.md                                # Claude Code project context (parent file)
```

## Setup

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY

# Ingest the live domains (fetches real university pages, builds Chroma)
python -m app.ingestion.run housing
python -m app.ingestion.run fees
python -m app.ingestion.run faculty
python -m app.ingestion.run student-employment
python -m app.ingestion.run programs

uvicorn app.main:app --reload
```

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How much does South Hall cost?"}'
```

Run the eval suite locally (from the repo root, same venv):

```bash
python -m eval.run_eval --all --gate        # Tier-1, LLM-judged
python -m eval.run_majors_eval --gate        # Majors state machine
python -m eval.run_router_eval --gate        # router/synthesis
```

## Git workflow

See `.claude/rules/git-workflow.md` for branch naming, commit conventions,
and the PR/merge flow used on this project.
