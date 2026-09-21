import os

import anthropic

from app.graph.majors_state import MajorsState
from app.retrieval.chroma_client import query_domain

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


DECLARE_SYSTEM_TEMPLATE = """A University of Memphis student wants to switch
to or declare {major} as their major. Using only the CONTEXT below,
explain how they actually do that. Cite the source URL.

CONTEXT:
{context}
"""


def majors_recommend(state: MajorsState) -> dict:
    """Declare-path only for now -- no competitive-major eligibility check
    or interrupt() yet, that lands once a real, verified competitive-major
    ruleset exists (see docs/domain-research/majors.md's scope decision).
    Every major reaching this node today gets the declare-path answer,
    which is correct for the overwhelming majority of real majors."""
    target_major = state["target_major"]

    hits = query_domain("programs", f"how do I change my major to {target_major}")
    sources = sorted({h["metadata"]["source_url"] for h in hits})
    context = "\n\n".join(
        f"[Source: {h['metadata']['source_url']}]\n{h['text']}" for h in hits
    )

    response = _get_client().messages.create(
        model="claude-sonnet-4-5",
        max_tokens=400,
        system=DECLARE_SYSTEM_TEMPLATE.format(major=target_major, context=context),
        messages=[{"role": "user", "content": f"How do I switch to {target_major}?"}],
    )
    answer = response.content[0].text

    return {
        "recommendation": {
            "path": "declare",
            "major": target_major,
            "eligibility_band": None,
            "sources": sources,
        },
        "recommendation_confirmed": True,
        "answer": answer,
    }
