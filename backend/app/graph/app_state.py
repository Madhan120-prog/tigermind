import operator
from typing import TypedDict, Annotated


def _reset_or_extend(existing: list[dict], update: list[dict] | None) -> list[dict]:
    """domain_results' reducer. Plain operator.add would carry a previous
    turn's results forward across the checkpointer -- domain_results is
    scratch state for exactly one turn's Tier-1 fan-out, not something
    meant to persist across separate /ask calls on the same thread_id.
    router emits None at the start of every turn to clear it via this
    reducer; the fan-out branches emit an actual list to accumulate within
    that one turn, same as operator.add would."""
    if update is None:
        return []
    return existing + update


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
    active_domains: list[str]

    # Tier-1 fan-out: one Send-based branch per active domain, each
    # carrying its own "domain" (this branch's single domain, read by
    # generic_domain_agent exactly like GraphState's old "domain" field)
    # and "retrieved", joining into domain_results before any merge.
    domain: str | None
    retrieved: list[dict]
    domain_results: Annotated[list[dict], _reset_or_extend]

    # Majors (Tier 2), unchanged from MajorsState.
    target_major: str | None
    interests: list[str]
    gpa: float | None
    prereq_gpa: float | None
    completed_courses: list[dict]
    ready_to_recommend: bool
    recommendation: dict | None
    recommendation_confirmed: bool | None
