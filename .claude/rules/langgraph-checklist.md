# LangGraph Gap Checklist

The purpose of this project is to prove real use of LangGraph's
primitives, not to reskin a hand-rolled router in LangGraph syntax. Before
calling any phase "done," verify against this list — see `PLAN.md`
Section 2 for why each item is load-bearing rather than decorative.

- [ ] **Checkpointer persists state across turns** — the Majors agent's
      `{interests, gpa, completed_courses}` state must survive between
      separate invocations of the graph (i.e., actually backed by a
      checkpointer, not held in a Python variable that resets per call).
- [ ] **Conditional edges genuinely change graph shape** — the router's
      output must determine which nodes actually execute (single-domain
      vs. multi-domain synthesizer path vs. Tier-3 auth-gated path), not
      just get logged and ignored while every node runs anyway.
- [ ] **`interrupt()` gates the Majors recommendation** — the
      declare-vs-apply output pauses for explicit confirmation before
      being treated as final, when GPA/prereq eligibility is borderline.
- [ ] **`interrupt()` gates every Phase 6 write action** — drop/add must
      pause for student confirmation before executing against the mock
      SIS. No write action fires without a human-confirmed resume.

If any of these end up not true by the time a phase is called complete,
that phase is not actually complete — fix it before moving to the next
phase, don't note it as a known gap and continue.
