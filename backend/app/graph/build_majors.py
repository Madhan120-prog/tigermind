from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.agents.majors_intake import majors_intake
from app.agents.majors_recommend import majors_recommend
from app.graph.majors_state import MajorsState


def _route_after_intake(state: MajorsState) -> str:
    return "recommend" if state.get("ready_to_recommend") else END


def build_majors_graph():
    """Tier 2's stateful flow -- deliberately separate from build_graph()
    (Tier 1's stateless graph). Not wired into /ask; must work standalone
    before Phase 4's router unifies everything (PLAN.md Section 13).

    checkpointer=MemorySaver() is what actually persists state across
    separate /majors/message calls sharing a thread_id -- lost on process
    restart, which is an accepted, documented tradeoff for a portfolio
    proof-of-concept (a durable backend is a deferred upgrade, not added
    speculatively). This graph and its checkpointer must stay a
    module-level singleton wherever it's used, exactly like the existing
    _graph = build_graph() pattern -- a fresh MemorySaver() per request
    would silently defeat persistence.
    """
    graph = StateGraph(MajorsState)
    graph.add_node("intake", majors_intake)
    graph.add_node("recommend", majors_recommend)
    graph.set_entry_point("intake")
    graph.add_conditional_edges(
        "intake", _route_after_intake, {"recommend": "recommend", END: END}
    )
    graph.add_edge("recommend", END)
    return graph.compile(checkpointer=MemorySaver())
