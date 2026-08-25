from langgraph.graph import END, StateGraph

from app.agents.generic_domain_agent import generic_domain_agent
from app.graph.guardrails import guardrails
from app.graph.state import GraphState


def build_graph():
    """Phase 1: a single domain, no router/synthesizer/checkpointer yet --
    those are Phase 3/4 concerns (see PLAN.md Section 13)."""
    graph = StateGraph(GraphState)
    graph.add_node("answer", generic_domain_agent)
    graph.add_node("guardrails", guardrails)
    graph.set_entry_point("answer")
    graph.add_edge("answer", "guardrails")
    graph.add_edge("guardrails", END)
    return graph.compile()
