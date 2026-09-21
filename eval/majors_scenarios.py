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
                    "My GPA is 3.6 and I've completed CHEM 1010 (A), "
                    "BIOL 2010 (A), BIOL 2020 (B), BIOL 1230 (A), "
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
                    "I want to apply to Nursing. My GPA is 3.6 and I "
                    "completed CHEM 1010 (A), BIOL 2010 (A), BIOL 2020 (B), "
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
]
