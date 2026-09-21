import operator
from typing import TypedDict, Annotated


class MajorsState(TypedDict):
    # operator.add on a list means LangGraph appends new messages to what's
    # already checkpointed for this thread, rather than overwriting it --
    # this is the actual mechanism that makes conversation history persist
    # across separate /majors/message calls.
    messages: Annotated[list[dict], operator.add]
    target_major: str | None
    interests: list[str]
    gpa: float | None
    completed_courses: list[dict]
    ready_to_recommend: bool
    recommendation: dict | None
    recommendation_confirmed: bool | None
    answer: str
