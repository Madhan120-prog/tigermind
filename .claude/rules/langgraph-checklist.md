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
- [ ] **Conditional edges genuinely change graph shape** — the router's
      output must determine which nodes actually execute (single-domain
      vs. multi-domain synthesizer path vs. Tier-3 auth-gated path), not
      just get logged and ignored while every node runs anyway. Still
      Phase 4 work. Majors' own `intake -> recommend` edge (Phase 3) is a
      smaller, verified instance of the same mechanism: a call with no
      GPA yet stays on `intake`, a call with GPA supplied moves to
      `recommend` — real branching, not the router itself.
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
