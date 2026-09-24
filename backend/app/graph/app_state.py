import operator
from typing import TypedDict, Annotated


class AppState(TypedDict):
    """One state schema behind the single /ask entry point, merging what
    used to be GraphState (Tier-1) and MajorsState (Tier-2) -- the router
    decides which fields matter for a given turn, but generic_domain_agent,
    majors_intake, and majors_recommend all read this same superset
    unchanged, since each only ever accesses the specific keys it already
    expects.
    """

    # Shared across every route.
    messages: Annotated[list[dict], operator.add]
    question: str
    answer: str
    sources: list[str]
    confidence_ok: bool
    deferred: bool

    # Router output.
    route: str | None
    domain: str | None

    # Tier-1 (single domain for now; generic_domain_agent and guardrails
    # are unchanged from Phase 1-2, so this matches GraphState exactly).
    retrieved: list[dict]

    # Majors (Tier 2), unchanged from MajorsState.
    target_major: str | None
    interests: list[str]
    gpa: float | None
    prereq_gpa: float | None
    completed_courses: list[dict]
    ready_to_recommend: bool
    recommendation: dict | None
    recommendation_confirmed: bool | None
