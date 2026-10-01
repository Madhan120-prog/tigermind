"""Scenarios exercising the router/synthesizer/guardrails wiring itself
(PLAN.md Section 13 Phase 4) -- eval_set.csv already proves per-domain
retrieval quality, and majors_scenarios.py already proves the Majors state
machine; what's new here is proving the router sends each question to the
right place, that a genuinely multi-domain question gets synthesized
instead of only ever answering one part, and that a synthesized answer
doesn't launder a deferral or drop a needed disclaimer along the way.
"""

SCENARIOS = [
    {
        "name": "single domain -- housing",
        "checks": "Router should classify this as tier1/housing, matching eval_set.csv's own expected answer.",
        "question": "How much does a semester in South Hall cost for 2026-27?",
        "expected": {"route": "tier1", "active_domains_set": ["housing"]},
    },
    {
        "name": "single domain -- fees",
        "checks": "Router should classify this as tier1/fees.",
        "question": "What is the late fee if my account isn't paid by the first day of classes?",
        "expected": {"route": "tier1", "active_domains_set": ["fees"]},
    },
    {
        "name": "single domain -- faculty",
        "checks": "Router should classify this as tier1/faculty.",
        "question": "What is Mark Sunderman's email and office location?",
        "expected": {"route": "tier1", "active_domains_set": ["faculty"]},
    },
    {
        "name": "single domain -- student-employment",
        "checks": "Router should classify this as tier1/student-employment.",
        "question": "How many hours a week can I work on campus during the semester?",
        # Routing only -- NOT asserting confidence_ok/deferred here. This
        # exact question is PLAN.md 17.13's known, accepted non-100% case
        # (the model sometimes volunteers an unrelated figure and the
        # guardrail's one retry doesn't always recover); that answer-
        # quality dimension is eval/run_eval.py's job (which already has
        # retry tolerance for it), not this routing check's.
        "expected": {"route": "tier1", "active_domains_set": ["student-employment"]},
    },
    {
        "name": "single domain -- programs",
        "checks": "A general (non-personalized) programs question should stay tier1/programs, not get pulled into the Majors flow.",
        "question": "What does the BSN Nursing program cover?",
        "expected": {"route": "tier1", "active_domains_set": ["programs"]},
    },
    {
        "name": "genuine multi-domain -- synthesizer fires",
        "checks": (
            "Question genuinely spans housing and student-employment -- router "
            "should return both domains, and the final answer should be one "
            "coherent, synthesized response citing both, not just one half "
            "answered."
        ),
        "question": "How much does South Hall cost per semester, and are there any on-campus jobs to help pay for it?",
        "expected": {
            "route": "tier1",
            "active_domains_set": ["housing", "student-employment"],
            "min_domain_results": 2,
        },
    },
    {
        "name": "deferral survives synthesis (regression check)",
        "checks": (
            "Same shape as the previous case, but the student-employment half "
            "triggers the international-hours deferral. The synthesized "
            "answer must keep that deferral's exact meaning intact -- no "
            "invented F-1 hours number -- and the housing half's dollar "
            "figures still need their freshness disclaimer even though the "
            "other half deferred."
        ),
        "question": (
            "How much does South Hall cost, and as an F-1 international "
            "student how many hours can I work on campus during school breaks?"
        ),
        # deferred=True is safe to assert here -- unlike scenario 4, the
        # question itself names "F-1 international student," which is a
        # question-triggered deferral (deterministic), not the probabilistic
        # answer-volunteered case 17.13 describes.
        "expected": {
            "route": "tier1",
            "active_domains_set": ["housing", "student-employment"],
            "deferred": True,
        },
    },
    {
        "name": "out of scope -- unclear",
        "checks": "Nothing here fits any domain or Majors -- should route 'unclear' with the deterministic fallback answer, never forced into the closest domain.",
        "question": "What's the weather like in Memphis today?",
        "expected": {"route": "unclear"},
    },
    {
        "name": "majors-flavored question routes to majors_intake, not programs",
        "checks": (
            "Personalized eligibility language ('can I get in with my GPA') "
            "should route to majors even though it names Nursing, which also "
            "exists in the programs domain -- proves the router draws the "
            "same general-vs-personalized line programs' own prompt_snippet "
            "already draws."
        ),
        "question": "Can I get into the Nursing program with my 3.6 GPA?",
        "expected": {"route": "majors"},
    },
]
