from langgraph.graph import END, StateGraph

from app.agents.generic_domain_agent import generic_domain_agent
from app.graph.app_state import AppState
from app.graph.guardrails import domain_guardrail_check, guardrails


def build_graph():
    """A single domain, no router -- kept deliberately separate from
    build_app.py's router-driven graph (Phase 4) as the tool for
    eval/run_eval.py's per-domain regression testing, which calls a domain
    directly so it can isolate retrieval quality from routing quality.
    Reuses the exact same node functions build_app.py's Tier-1 path uses,
    including the per-domain guardrail check, so this harness never drifts
    from what a real request actually runs."""
    graph = StateGraph(AppState)
    graph.add_node("answer", generic_domain_agent)
    graph.add_node("domain_guardrail_check", domain_guardrail_check)
    graph.add_node("guardrails", guardrails)
    graph.set_entry_point("answer")
    graph.add_edge("answer", "domain_guardrail_check")
    graph.add_edge("domain_guardrail_check", "guardrails")
    graph.add_edge("guardrails", END)
    return graph.compile()
