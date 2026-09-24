# LangGraph Gap Checklist

The purpose of this project is to prove real use of LangGraph's
primitives, not to reskin a hand-rolled router in LangGraph syntax. Before
calling any phase "done," verify against this list — see `PLAN.md`
Section 2 for why each item is load-bearing rather than decorative.

- [x] **Checkpointer persists state across turns** — the Majors agent's
      `{interests, gpa, completed_courses}` state must survive between
      separate invocations of the graph (i.e., actually backed by a
      checkpointer, not held in a Python variable that resets per call).
      Done in Phase 3: `MemorySaver`, module-level singleton alongside
      `build_majors_graph()`. Verified against a real running server, not
      just the compiled graph: killed and restarted `uvicorn` and
      confirmed the same `thread_id` came back with no memory of the
      paused conversation, proving persistence is real (and bounded to
      the process lifetime — a documented tradeoff, not a hidden one).
      `build_majors_graph()` itself was superseded in Phase 4 by the one
      router-driven `build_app_graph()`, same `MemorySaver` singleton
      pattern, same guarantee — re-verified live against the new graph.
- [x] **Conditional edges genuinely change graph shape** — the router's
      output must determine which nodes actually execute (single-domain
      vs. multi-domain synthesizer path vs. Tier-3 auth-gated path), not
      just get logged and ignored while every node runs anyway. Done in
      Phase 4: a real tool-calling router (`route`: `tier1`/`majors`/
      `unclear`, plus which domain(s) when `tier1`) determines the actual
      graph path taken — `unclear` never touches retrieval or guardrails
      at all, `majors` enters the Phase 3 state machine, and `tier1` fans
      out via `langgraph.types.Send` to one `generic_domain_agent` call
      per active domain, only running the synthesizer when more than one
      domain actually fired. Verified live: a single-domain question
      takes the direct path, a genuinely multi-topic question visibly
      produces more than one `domain_results` entry and reaches the
      synthesizer, and an out-of-scope question never reaches retrieval.
      The Tier-3 auth-gated path isn't part of this yet — it doesn't exist
      until Phase 6. Majors' own `intake -> recommend` edge (Phase 3)
      remains a smaller, separately-verified instance of the same
      mechanism.
- [x] **`interrupt()` gates the Majors recommendation** — the
      declare-vs-apply output pauses for explicit confirmation before
      being treated as final, when GPA/prereq eligibility is borderline.
      Done in Phase 3 against one real, verified competitive-major
      ruleset (Nursing): fires only for a genuinely borderline case, not
      for clearly eligible or clearly ineligible, and both confirming and
      declining the pause were tested and behave correctly (declining
      holds off the verdict entirely rather than showing it anyway).
- [ ] **`interrupt()` gates every Phase 6 write action** — drop/add must
      pause for student confirmation before executing against the mock
      SIS. No write action fires without a human-confirmed resume. Not
      yet built — Phase 6.

If any of these end up not true by the time a phase is called complete,
that phase is not actually complete — fix it before moving to the next
phase, don't note it as a known gap and continue.
