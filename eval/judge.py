"""LLM-as-judge grading, shared by every eval runner's --gate mode.

The eval set's expected answers are prose ("Up to 25 hours/week during
Fall and Spring..."), not exact strings or source URLs, and PLAN.md 17.11
already found that answer wording varies slightly run to run -- so exact/
substring matching would false-fail a correctly-phrased-differently
answer. A forced tool-call verdict (the same pattern already used by
majors_intake.py and router.py) compares meaning, not wording.
"""
import os

import anthropic

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


JUDGE_TOOL = {
    "name": "judge_answer",
    "description": "Decide whether an AI assistant's actual answer to a student's question is correct, compared to a known-correct expected answer.",
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["pass", "fail"],
                "description": (
                    "'pass' only if the actual answer states the same key "
                    "facts as the expected answer and does not claim "
                    "anything the expected answer implies it shouldn't "
                    "(e.g. naming something as a major that the expected "
                    "answer says is actually a minor). Close paraphrasing, "
                    "different ordering, and extra correct detail are all "
                    "fine -- grade meaning, not wording."
                ),
            },
            "reason": {
                "type": "string",
                "description": "One sentence explaining the verdict.",
            },
        },
        "required": ["verdict", "reason"],
    },
}

JUDGE_SYSTEM = """You grade whether an AI assistant's actual answer to a
University of Memphis student's question is correct, by comparing it
against a known-correct expected answer. Grade meaning, not wording --
paraphrasing, different ordering, and extra correct detail are all fine.
Fail the answer if it misses a key fact the expected answer states, states
something factually wrong, or claims something the expected answer
specifically implies is incorrect (several expected answers are precision
cases calling out exactly what a wrong answer would claim)."""


def judge(question: str, expected: str, actual: str) -> tuple[str, str]:
    """Returns (verdict, reason) -- verdict is 'pass' or 'fail'."""
    response = _get_client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=200,
        system=JUDGE_SYSTEM,
        tools=[JUDGE_TOOL],
        tool_choice={"type": "tool", "name": "judge_answer"},
        messages=[
            {
                "role": "user",
                "content": f"Question: {question}\n\nExpected answer: {expected}\n\nActual answer: {actual}",
            }
        ],
    )
    result = next(
        block.input for block in response.content if block.type == "tool_use"
    )
    return result["verdict"], result["reason"]
