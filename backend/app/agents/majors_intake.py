import os

import anthropic

from app.config.competitive_majors import match_competitive_major
from app.graph.app_state import AppState

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
                "description": "The student's overall cumulative GPA, if mentioned. Null if not mentioned.",
            },
            "prereq_gpa": {
                "type": ["number", "null"],
                "description": "The student's GPA specifically in a major's required prerequisite courses, if mentioned separately from their overall cumulative GPA. Null if not mentioned or not distinguished from the cumulative figure.",
            },
            "completed_courses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Course code, normalized to SUBJECT #### form (e.g. 'CHEM 1010'), regardless of how the student wrote it.",
                        },
                        "status": {
                            "type": "string",
                            "enum": ["completed", "in_progress"],
                            "description": "'completed' if the student has already taken and been graded, 'in_progress' if they're currently taking it or say it's not done yet.",
                        },
                        "grade": {
                            "type": ["string", "null"],
                            "description": "The grade received. Null when status is 'in_progress', since there's no grade yet.",
                        },
                    },
                    "required": ["code", "status", "grade"],
                },
                "description": "Specific courses the student has mentioned, completed or in progress, with grades where given.",
            },
        },
        "required": ["target_major", "interests", "gpa", "prereq_gpa", "completed_courses"],
    },
}

SYSTEM = """You are gathering information to advise a University of Memphis
student about choosing or changing their major. Read the ENTIRE
conversation so far and extract everything currently known -- not just
this turn's message, since earlier turns may have named a major or GPA
that this turn doesn't repeat. Do not guess at a value the student never
stated; leave it null or empty instead. Cumulative GPA and
prerequisite-specific GPA are two different numbers for competitive
majors -- only fill in prereq_gpa when the student actually distinguishes
it from their overall GPA, never copy the cumulative figure into it."""

NO_MAJOR_QUESTION = (
    "Tell me a bit more -- what major are you considering, or if you're "
    "not sure yet, what subjects or interests are you drawn to?"
)


def _competitive_clarifying_question(major_name: str, gpa, prereq_gpa, completed_courses) -> str:
    if gpa is None:
        return (
            f"{major_name} has GPA-based admission requirements. What's your "
            "current cumulative GPA?"
        )
    if prereq_gpa is None:
        return (
            f"Thanks -- {major_name} also looks at your GPA specifically in "
            "its required prerequisite courses, which is separate from your "
            "overall GPA. Do you know that number? If not, just tell me "
            "which prerequisite courses you've taken (or are taking) and "
            "what grades you got."
        )
    if not completed_courses:
        return (
            f"And have you completed (or are you working on) any of "
            f"{major_name}'s prerequisite courses? Which ones, and what grades?"
        )
    return ""


def majors_intake(state: AppState) -> dict:
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
    gpa = extracted["gpa"]
    prereq_gpa = extracted["prereq_gpa"]
    completed_courses = extracted["completed_courses"]

    if target_major is None:
        ready, answer = False, NO_MAJOR_QUESTION
    else:
        competitive = match_competitive_major(target_major)
        if competitive is None:
            # Declare path: no GPA/prereq gate exists, so nothing more is
            # needed once the major itself is named.
            ready, answer = True, ""
        else:
            # Competitive path: needs enough to make a real judgment --
            # cumulative GPA plus at least one reported course. prereq_gpa
            # is asked for but not required to proceed -- if still unknown
            # once we reach recommend, the eligibility check treats that as
            # unverified rather than assuming it matches the cumulative
            # figure (that assumption is exactly what produced a false
            # clearly_eligible before).
            ready = gpa is not None and len(completed_courses) > 0
            answer = (
                ""
                if ready
                else _competitive_clarifying_question(
                    competitive.display_name, gpa, prereq_gpa, completed_courses
                )
            )

    return {
        "target_major": target_major,
        "interests": extracted["interests"],
        "gpa": gpa,
        "prereq_gpa": prereq_gpa,
        "completed_courses": completed_courses,
        "ready_to_recommend": ready,
        "answer": answer,
    }
