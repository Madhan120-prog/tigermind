from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.agents.generic_domain_agent import generic_domain_agent
from app.agents.majors_intake import majors_intake
from app.agents.majors_recommend import majors_recommend
from app.agents.router import router
from app.graph.app_state import AppState
from app.graph.guardrails import guardrails


def _route_from_router(state: AppState) -> str:
    route = state["route"]
    if route == "majors":
        return "majors_intake"
    if route == "tier1":
        return "generic_domain_agent"
    return END  # "unclear" -- router already filled in the answer itself


def _route_after_intake(state: AppState) -> str:
    return "majors_recommend" if state.get("ready_to_recommend") else END


def build_app_graph():
    """The one graph behind /ask, replacing both the old no-router
    build_graph() path and the separate build_majors_graph() -- a real
    router decides per turn whether this is a Tier-1 factual question, a
    personalized Majors question, or out of scope (PLAN.md Section 13
    Phase 4). generic_domain_agent, majors_intake, majors_recommend, and
    guardrails are reused completely unchanged from Phases 1-3; only the
    router is new.

    Single Tier-1 domain per turn for now -- fanning out over multiple
    domains and a synthesizer node land in a later commit on this branch.
    majors_recommend still edges straight to END rather than guardrails;
    extending guardrails to cover Majors' answers is also a later commit.

    checkpointer=MemorySaver() must stay a module-level singleton wherever
    this is used (same caveat as the old build_majors_graph()) -- lost on
    process restart, an accepted tradeoff, not added speculatively.
    """
    graph = StateGraph(AppState)
    graph.add_node("router", router)
    graph.add_node("majors_intake", majors_intake)
    graph.add_node("majors_recommend", majors_recommend)
    graph.add_node("generic_domain_agent", generic_domain_agent)
    graph.add_node("guardrails", guardrails)

    graph.set_entry_point("router")
    graph.add_conditional_edges(
        "router",
        _route_from_router,
        {"majors_intake": "majors_intake", "generic_domain_agent": "generic_domain_agent", END: END},
    )
    graph.add_conditional_edges(
        "majors_intake", _route_after_intake, {"majors_recommend": "majors_recommend", END: END}
    )
    graph.add_edge("majors_recommend", END)
    graph.add_edge("generic_domain_agent", "guardrails")
    graph.add_edge("guardrails", END)
    return graph.compile(checkpointer=MemorySaver())
