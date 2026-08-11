---
name: ingest-domain
description: Scrape, chunk, embed, and verify one Tier-1 domain's data into its Chroma collection. Invoke when bringing a new domain online or re-ingesting a stale one.
---

# Ingest Domain

Mechanical procedure for the scrape → chunk → embed → verify loop used by
every Tier-1 domain (`PLAN.md` Section 4). Retrieval-strategy judgment
calls (structured vs. semantic vs. hybrid, chunk size, freshness tier) are
made once in Phase 0 domain reconnaissance and recorded in
`docs/domain-research/{domain}.md` — this skill executes that decision
mechanically, it does not re-derive it. For the mechanical execution
itself, delegate to the `domain-ingestor` subagent
(`.claude/agents/domain-ingestor.md`).

## Steps

1. **Read the domain's research doc** — `docs/domain-research/{domain}.md`
   — for source URL(s), format, and the chosen retrieval mode.
2. **Scrape** the source into `backend/data/raw/{domain}/` (gitignored).
   Preserve the source URL and a fetch timestamp per page/file.
3. **Chunk** according to the retrieval mode in the research doc: prose
   sections for semantic domains, structured records (one per course code
   / faculty entry / event) for structured/hybrid domains.
4. **Embed** each chunk with `sentence-transformers` and upsert into the
   domain's Chroma collection, keyed by content hash so re-running
   ingestion is idempotent (updates existing chunks, doesn't duplicate
   them).
5. **Attach metadata** on every chunk: `domain`, `source_url`,
   `last_updated`, and `freshness_tier` (`slow` or `fast`, per `PLAN.md`
   Section 7).
6. **Add one entry** to `backend/app/config/domains.yaml` for this domain
   (collection name, retrieval mode, prompt snippet) if it doesn't exist
   yet — this is the only code-adjacent change; no new agent function.
7. **Verify**: run 2-3 sample queries against the new collection directly
   (before wiring into the graph) and confirm retrieved chunks are
   relevant and carry correct metadata.
8. **Seed eval rows**: add the domain's 5 rough Q&A pairs from Phase 0 into
   `eval/eval_set.csv` if not already present.
