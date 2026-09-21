import os

import anthropic

from app.graph.majors_state import MajorsState

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


EXTRACT_TOOL = {
    "name": "update_intake",
    "description": (
        "Record what is currently known about the student's major interests "
        "and academic standing, based on the whole conversation so far."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "target_major": {
                "type": ["string", "null"],
                "description": "The specific major the student wants to declare or apply to, if named. Null if not yet mentioned.",
            },
            "interests": {
                "type": "array",
                "items": {"type": "string"},
                "description": "General interests/subjects the student has mentioned, useful when they haven't named a specific major.",
            },
            "gpa": {
                "type": ["number", "null"],
                "description": "The student's cumulative GPA, if mentioned. Null if not mentioned.",
            },
            "completed_courses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "grade": {"type": "string"},
                    },
                    "required": ["code", "grade"],
                },
                "description": "Specific courses and grades the student has mentioned completing.",
            },
        },
        "required": ["target_major", "interests", "gpa", "completed_courses"],
    },
}

SYSTEM = """You are gathering information to advise a University of Memphis
student about choosing or changing their major. Read the ENTIRE
conversation so far and extract everything currently known -- not just
this turn's message, since earlier turns may have named a major or GPA
that this turn doesn't repeat. Do not guess at a value the student never
stated; leave it null or empty instead."""

CLARIFYING_QUESTION = (
    "Tell me a bit more -- what major are you considering, or if you're "
    "not sure yet, what subjects or interests are you drawn to?"
)


def majors_intake(state: MajorsState) -> dict:
    """Re-derives the full known state from the whole conversation each
    turn, rather than incrementally merging one message at a time -- this
    avoids stale fields drifting out of sync with what the student has
    actually said, at the cost of one extra tokens-in-context turn."""
    response = _get_client().messages.create(
        model="claude-sonnet-4-5",
        max_tokens=600,
        system=SYSTEM,
        tools=[EXTRACT_TOOL],
        tool_choice={"type": "tool", "name": "update_intake"},
        messages=state["messages"],
    )
    extracted = next(
        block.input for block in response.content if block.type == "tool_use"
    )

    target_major = extracted["target_major"]
    ready = target_major is not None

    return {
        "target_major": target_major,
        "interests": extracted["interests"],
        "gpa": extracted["gpa"],
        "completed_courses": extracted["completed_courses"],
        "ready_to_recommend": ready,
        "answer": "" if ready else CLARIFYING_QUESTION,
    }
