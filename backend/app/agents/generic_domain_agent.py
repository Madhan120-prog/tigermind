import os

import anthropic

from app.config.loader import get_domain
from app.graph.state import GraphState
from app.retrieval.chroma_client import query_domain

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


SYSTEM_TEMPLATE = """{prompt_snippet}

Answer only from the CONTEXT below. If the context doesn't contain a
confident answer, say so explicitly instead of guessing. Cite the source
URL for every factual claim.

CONTEXT:
{context}
"""


def generic_domain_agent(state: GraphState) -> dict:
    """One function for every Tier-1 domain -- behavior comes entirely from
    the domain's config entry, never a per-domain code branch."""
    config = get_domain(state["domain"])
    hits = query_domain(config.collection, state["question"])

    context = "\n\n".join(
        f"[Source: {h['metadata']['source_url']}]\n{h['text']}" for h in hits
    )
    system = SYSTEM_TEMPLATE.format(
        prompt_snippet=config.prompt_snippet, context=context
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
