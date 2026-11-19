from app.graph.app_state import AppState
from app.llm_client import complete


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

    response = complete(
        system=SYSTEM_TEMPLATE.format(sections=sections),
        messages=[{"role": "user", "content": state["question"]}],
        model="claude-sonnet-4-5",
        max_tokens=700,
    )

    sources = sorted({source for r in results for source in r["sources"]})
    return {"answer": response.text, "sources": sources}
