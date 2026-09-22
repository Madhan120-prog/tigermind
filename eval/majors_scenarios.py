"""Multi-turn conversation scenarios for the stateful Majors flow.

eval_set.csv's one-row-per-question shape can't represent a paused,
multi-turn conversation with a confirm/decline step in the middle -- this
is a separate, small structure instead of forcing a resume step into a
CSV cell. Each scenario names which langgraph-checklist.md item it proves.
"""

SCENARIOS = [
    {
        "name": "A - checkpointer persistence",
        "checks": (
            "Turn 1's reported interests should still be present in state "
            "after turn 2, which never repeats them -- only holds if the "
            "checkpointer actually persisted turn 1's extraction."
        ),
        "turns": [
            {"kind": "message", "content": "I'm not sure what to study yet, but I like biology and helping people"},
            {"kind": "message", "content": "What about Computer Science instead?"},
        ],
    },
    {
        "name": "B - conditional edge (ask more vs. proceed)",
        "checks": (
            "Turn 1 (no GPA yet) should NOT reach the recommend node -- no "
            "recommendation in state, a clarifying question as the answer. "
            "Turn 2 (GPA + prereqs given) should reach recommend and "
            "produce a clearly_eligible read."
        ),
        "turns": [
            {"kind": "message", "content": "I want to apply to Nursing"},
            {
                "kind": "message",
                "content": (
                    "My cumulative GPA is 3.6 and my GPA specifically in my "
                    "prerequisite courses is 3.5. I've completed CHEM 1010 "
                    "(A), BIOL 2010 (A), BIOL 2020 (B), BIOL 1230 (A), "
                    "MATH 1530 (B), NUTR 2202 (A), EDPR 2111 (B)"
                ),
            },
        ],
    },
    {
        "name": "C - interrupt() fires and resumes (borderline)",
        "checks": (
            "GPA 2.9 sits inside Nursing's borderline margin band around "
            "the real 3.0 cutoff -- should pause for confirmation. "
            "Confirming should deliver the honest final verdict (2.9 is "
            "still below 3.0), not a softened one."
        ),
        "turns": [
            {
                "kind": "message",
                "content": (
                    "I want to apply to Nursing. My GPA is 2.9 and I "
                    "completed CHEM 1010 (B), BIOL 2010 (B), BIOL 2020 (B), "
                    "BIOL 1230 (B), MATH 1530 (B), NUTR 2202 (B), "
                    "EDPR 2111 (B)"
                ),
            },
            {"kind": "resume", "content": "yes, finalize it"},
        ],
    },
    {
        "name": "C2 - interrupt() fires and declines (borderline)",
        "checks": (
            "Same borderline case, but declining should hold off entirely "
            "-- no eligibility verdict shown, just an acknowledgment -- not "
            "show the verdict anyway."
        ),
        "turns": [
            {
                "kind": "message",
                "content": (
                    "I want to apply to Nursing. My GPA is 2.9 and I "
                    "completed CHEM 1010 (B), BIOL 2010 (B), BIOL 2020 (B), "
                    "BIOL 1230 (B), MATH 1530 (B), NUTR 2202 (B), "
                    "EDPR 2111 (B)"
                ),
            },
            {"kind": "resume", "content": "no, let me improve my numbers first"},
        ],
    },
    {
        "name": "D - interrupt() does not fire (clearly eligible)",
        "checks": (
            "GPA 3.6, well above threshold plus margin, all prereqs at or "
            "above the minimum grade -- should answer directly, no pause."
        ),
        "turns": [
            {
                "kind": "message",
                "content": (
                    "I want to apply to Nursing. My cumulative GPA is 3.6 "
                    "and my prerequisite-specific GPA is 3.5. I completed "
                    "CHEM 1010 (A), BIOL 2010 (A), BIOL 2020 (B), "
                    "BIOL 1230 (A), MATH 1530 (B), NUTR 2202 (A), "
                    "EDPR 2111 (B)"
                ),
            },
        ],
    },
    {
        "name": "E - interrupt() does not fire (clearly ineligible)",
        "checks": (
            "GPA 2.2, well below threshold minus margin -- should answer "
            "directly and honestly, no pause, no false hope."
        ),
        "turns": [
            {
                "kind": "message",
                "content": (
                    "I want to apply to Nursing. My GPA is 2.2 and I "
                    "completed CHEM 1010 (C), BIOL 2010 (C)"
                ),
            },
        ],
    },
    {
        "name": "F - high GPA but unrelated/failing courses (regression check)",
        "checks": (
            "GPA 3.5 (well above threshold+margin) but the reported courses "
            "are none of Nursing's actual prerequisites, and one is a "
            "failing grade. This must NOT score clearly_eligible on course "
            "count alone -- real course-code and grade matching should "
            "classify every required prerequisite as pending (not "
            "reported), landing this in borderline, not a false positive."
        ),
        "turns": [
            {
                "kind": "message",
                "content": (
                    "I want to apply to Nursing. My GPA is 3.5. I've "
                    "completed ENGL 1010 (A), HIST 2010 (F), ART 1030 (A), "
                    "PHIL 1101 (A), DANC 1000 (A), MUS 1030 (A), "
                    "THEA 1030 (A)"
                ),
            },
        ],
    },
    {
        "name": "G - in-progress prerequisite (schema fix check)",
        "checks": (
            "GPA well above threshold on both cumulative and "
            "prerequisite-specific figures, all prerequisites verified "
            "complete except one explicitly in progress. Must be "
            "representable at all (the old schema required a grade for "
            "every course) and, per policy, an in-progress prerequisite is "
            "not itself a borderline signal -- this should land in "
            "clearly_eligible, not borderline, proving in-progress no "
            "longer over-corrects into an automatic pause."
        ),
        "turns": [
            {
                "kind": "message",
                "content": (
                    "I want to apply to Nursing. My cumulative GPA is 3.5 "
                    "and my prerequisite-specific GPA is 3.5. I've "
                    "completed CHEM 1010 (A), BIOL 2010 (A), BIOL 2020 (A), "
                    "BIOL 1230 (A), MATH 1530 (A), NUTR 2202 (A), and I'm "
                    "currently taking EDPR 2111 right now, not done yet"
                ),
            },
        ],
    },
    {
        "name": "H - strong cumulative GPA masking a weak prerequisite GPA (regression check)",
        "checks": (
            "Cumulative GPA 3.6 is well above the 3.0 threshold, but the "
            "prerequisite-specific GPA is 2.5 -- clearly below it. A "
            "single collapsed GPA figure previously let the strong "
            "cumulative number stand in for both checks, scoring this "
            "clearly_eligible. With cumulative and prerequisite GPA scored "
            "independently, the failing prerequisite GPA should land this "
            "in clearly_ineligible instead."
        ),
        "turns": [
            {
                "kind": "message",
                "content": (
                    "I want to apply to Nursing. My cumulative GPA is 3.6 "
                    "but my GPA specifically in my prerequisite courses is "
                    "2.5. I've completed CHEM 1010 (C), BIOL 2010 (C), "
                    "BIOL 2020 (C), BIOL 1230 (C), MATH 1530 (C), "
                    "NUTR 2202 (C), EDPR 2111 (C)"
                ),
            },
        ],
    },
]
