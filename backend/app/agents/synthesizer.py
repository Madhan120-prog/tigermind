import os

import anthropic

from app.graph.app_state import AppState

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


SYSTEM_TEMPLATE = """A University of Memphis student asked one question that
touches more than one topic. Below is an already-finalized answer for each
relevant topic -- each one has already been checked for confidence and
safety. Do not re-derive, re-check, re-word, or soften any fact, number,
or deferral in them; your only job is to weave them into one clear,
well-organized response that reads naturally instead of like separate
answers stapled together. If one topic's answer says it couldn't find a
confident answer, or defers to an office instead of answering, keep that
exact meaning intact -- never smooth it into something that sounds more
confident than the source answer actually was.

TOPIC ANSWERS:
{sections}
"""


def synthesizer(state: AppState) -> dict:
    results = state["domain_results"]
    sections = "\n\n".join(f"[{r['domain']}]\n{r['answer']}" for r in results)

    response = _get_client().messages.create(
        model="claude-sonnet-4-5",
        max_tokens=700,
        system=SYSTEM_TEMPLATE.format(sections=sections),
        messages=[{"role": "user", "content": state["question"]}],
    )

    sources = sorted({source for r in results for source in r["sources"]})
    return {"answer": response.content[0].text, "sources": sources}
