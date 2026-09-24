from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Send

from app.agents.generic_domain_agent import generic_domain_agent, retry_constraint_for
from app.agents.majors_intake import majors_intake
from app.agents.majors_recommend import majors_recommend
from app.agents.router import router
from app.agents.synthesizer import synthesizer
from app.graph.app_state import AppState
from app.graph.guardrails import check_domain, guardrails


def _tier1_domain_pipeline(state: AppState) -> dict:
    """Send's target for the Tier-1 fan-out. generic_domain_agent and the
    per-domain guardrail check have to run here as one atomic write, not
    as two separate graph nodes joined by a normal edge -- Send only
    supplies its payload as input to this one invocation, it doesn't
    persist "domain" into the shared graph state for a downstream node to
    read, and with more than one domain active, concurrent branches
    writing a plain (non-reducer) "domain" key at the same step would
    conflict outright. domain_results is the one thing this writes back,
    and it's Annotated with operator.add specifically so every branch's
    write merges instead of colliding.
    """
    domain_output = generic_domain_agent(state)

    def regenerate(deferral: dict) -> str:
        return generic_domain_agent(state, extra_constraint=retry_constraint_for(deferral))["answer"]

    checked = check_domain(
        state["domain"],
        state["question"],
        domain_output["retrieved"],
        domain_output["answer"],
        domain_output["sources"],
        regenerate=regenerate,
    )
    return {"domain_results": [checked]}


def _route_from_router(state: AppState):
    route = state["route"]
    if route == "majors":
        return "majors_intake"
    if route == "tier1":
        # Fans out to one _tier1_domain_pipeline invocation per active
        # domain -- each Send carries its own isolated input (just the one
        # domain + the shared question), joining back into domain_results
        # once every branch has run. This is the real conditional edge
        # that changes the graph's shape per question, not just a
        # logged-and-ignored classification.
        return [
            Send("tier1_domain", {"domain": domain, "question": state["question"]})
            for domain in state["active_domains"]
        ]
    return END  # "unclear" -- router already filled in the answer itself


def _route_after_intake(state: AppState) -> str:
    return "majors_recommend" if state.get("ready_to_recommend") else END


def _join_domain_results(state: AppState) -> dict:
    """A plain node every tier1_domain branch feeds into via a normal edge,
    existing purely as a join barrier -- a conditional edge attached
    directly to a Send-targeted node gets evaluated once per branch as
    each one finishes, not once after all of them merge, so with more than
    one active domain it could see a partial domain_results and route
    prematurely. Routing from this node instead guarantees every branch
    has already merged in by the time _route_after_domain_check runs.
    """
    return {}


def _route_after_domain_check(state: AppState) -> str:
    # Synthesis only when the question genuinely spanned more than one
    # domain -- PLAN.md Section 5's rule that the synthesizer doesn't run
    # on every request, only when there's actually more than one answer to
    # merge.
    return "synthesizer" if len(state["domain_results"]) > 1 else "guardrails"


def build_app_graph():
    """The one graph behind /ask, replacing both the old no-router
    build_graph() path and the separate build_majors_graph() -- a real
    router decides per turn whether this is a Tier-1 factual question
    (possibly spanning more than one domain), a personalized Majors
    question, or out of scope (PLAN.md Section 13 Phase 4).
    generic_domain_agent, majors_intake, majors_recommend, and guardrails'
    per-domain check are reused completely unchanged; only the router and
    synthesizer are new.

    Per-domain confidence/deferral checks (domain_guardrail_check) happen
    on every branch BEFORE synthesis, never after -- a low-confidence or
    deferred sub-answer must be settled before an LLM synthesizer ever
    sees it, or synthesis could smooth it into fluent, confident prose and
    launder exactly the kind of fabricated figure guardrails.md exists to
    catch.

    majors_recommend's final answer also flows through guardrails now
    (majors_intake's "not ready yet" clarifying question still doesn't --
    there's no retrieval or citation in a bare question to check).

    checkpointer=MemorySaver() must stay a module-level singleton wherever
    this is used (same caveat as the old build_majors_graph()) -- lost on
    process restart, an accepted tradeoff, not added speculatively.
    """
    graph = StateGraph(AppState)
    graph.add_node("router", router)
    graph.add_node("majors_intake", majors_intake)
    graph.add_node("majors_recommend", majors_recommend)
    graph.add_node("tier1_domain", _tier1_domain_pipeline)
    graph.add_node("join_domain_results", _join_domain_results)
    graph.add_node("synthesizer", synthesizer)
    graph.add_node("guardrails", guardrails)

    graph.set_entry_point("router")
    graph.add_conditional_edges("router", _route_from_router)
    graph.add_conditional_edges(
        "majors_intake", _route_after_intake, {"majors_recommend": "majors_recommend", END: END}
    )
    graph.add_edge("majors_recommend", "guardrails")
    graph.add_edge("tier1_domain", "join_domain_results")
    graph.add_conditional_edges(
        "join_domain_results",
        _route_after_domain_check,
        {"synthesizer": "synthesizer", "guardrails": "guardrails"},
    )
    graph.add_edge("synthesizer", "guardrails")
    graph.add_edge("guardrails", END)
    return graph.compile(checkpointer=MemorySaver())
