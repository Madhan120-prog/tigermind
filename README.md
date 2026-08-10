# TigerGuide

A LangGraph-based multi-agent assistant answering University of Memphis
student questions across housing, fees, registration, majors, faculty, and
campus employment.

Built as a second, framework-based data point on multi-agent orchestration,
alongside the hand-rolled Integrated Patient System project. See `PLAN.md`
for the full rationale, phased build plan, and what has to be true for this
to actually close that gap rather than reskin it.

## Status

Pre-implementation. Repo scaffolding and planning docs only — see `PLAN.md`
Phase 0 for the current step.

## Tech stack

| Layer | Choice |
|---|---|
| Backend | FastAPI |
| Orchestration | LangGraph (StateGraph, conditional edges, checkpointer) |
| Vector store | Chroma, domain-scoped collections |
| Embeddings | Local `sentence-transformers` |
| Frontend | React (reused chat component from the patient-system project) |

Full reasoning for each choice — and the alternatives considered — lives in
the project discussion; ask in a Claude Code session if you want it
re-derived, or see the conversation history where this was decided.

## Folder structure

```
tigerguide/
├── .claude/
│   ├── agents/          # Subagent definitions (isolated context, own model)
│   ├── rules/           # Always-loaded conventions (architecture, git, guardrails)
│   └── skills/          # On-demand procedures (e.g. domain ingestion)
├── backend/
│   ├── app/
│   │   ├── agents/      # Specialist agent nodes (housing, fees, registration, majors)
│   │   ├── graph/        # Router, synthesizer, guardrails, LangGraph state
│   │   ├── ingestion/     # Scrape -> chunk -> embed pipeline, per domain
│   │   ├── retrieval/     # Chroma client, structured lookup helpers
│   │   └── main.py         # FastAPI entrypoint
│   ├── data/
│   │   ├── raw/            # Scraped source pages (gitignored)
│   │   └── chroma/          # Vector store persistence (gitignored)
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/              # Reused React chat component
├── eval/
│   ├── eval_set.csv        # Question/domain/expected-answer pairs
│   └── run_eval.py
├── docs/
│   └── domain-research/    # Phase 0 reconnaissance per domain
├── PLAN.md                 # Full build plan, phases, checkpoints
└── CLAUDE.md                # Claude Code project context (parent file)
```

## Setup

Not yet implemented — see `PLAN.md` Phase 0 and Phase 1 for what comes first.

## Git workflow

See `.claude/rules/git-workflow.md` for branch naming, commit conventions,
and the PR/merge flow used on this project.
