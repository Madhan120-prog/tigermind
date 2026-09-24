import os

import anthropic

from app.config.loader import get_domain
from app.graph.app_state import AppState
from app.retrieval.chroma_client import query_domain

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


SYSTEM_TEMPLATE = """{prompt_snippet}
{deferral_constraint}
Answer only from the CONTEXT below. If the context doesn't contain a
confident answer, say so explicitly instead of guessing. Cite the source
URL for every factual claim.

CONTEXT:
{context}
"""

DEFERRAL_CONSTRAINT_TEMPLATE = """
Never state a number, limit, deadline or eligibility rule concerning
{topics}, and never volunteer one the student did not ask for. Name
{refer_to} as the place to get an authoritative answer and say nothing
further on it -- including when the context below appears to contain a
figure, since sources on this topic are known to disagree.
"""


def _deferral_constraint(deferrals: list[dict]) -> str:
    """Turn a domain's configured deferrals into a prompt constraint.

    Guardrails already refuse an answer that asserts a figure on a deferred
    topic, but refusing after the fact means a sound answer gets replaced
    because the model wandered into visa limits unprompted -- which is
    exactly what happened to two passing questions. Instruct first, verify
    second: the guardrail becomes a net rather than the mechanism.
    """
    return "".join(
        DEFERRAL_CONSTRAINT_TEMPLATE.format(
            topics=", ".join(deferral["triggers"]),
            refer_to=" ".join(deferral["refer_to"].split()),
        )
        for deferral in deferrals
    )


def generic_domain_agent(state: AppState) -> dict:
    """One function for every Tier-1 domain -- behavior comes entirely from
    the domain's config entry, never a per-domain code branch."""
    config = get_domain(state["domain"])
    hits = query_domain(config.collection, state["question"], mode=config.retrieval_mode)

    context = "\n\n".join(
        f"[Source: {h['metadata']['source_url']}]\n{h['text']}" for h in hits
    )
    system = SYSTEM_TEMPLATE.format(
        prompt_snippet=config.prompt_snippet,
        deferral_constraint=_deferral_constraint(config.deferrals),
        context=context,
    )

    response = _get_client().messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        system=system,
        messages=[{"role": "user", "content": state["question"]}],
    )
    answer = response.content[0].text

    sources = sorted({h["metadata"]["source_url"] for h in hits})
    return {
        "retrieved": hits,
        "answer": answer,
        "sources": sources,
    }
