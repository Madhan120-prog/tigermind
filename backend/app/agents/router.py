import os

import anthropic

from app.config.loader import load_domains
from app.graph.app_state import AppState

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


MAJORS_DESCRIPTION = """Personalized major advising: a student expressing
their own intent to apply to, declare, or get into a specific major, even
before they've given any numbers yet -- "I want to apply to Nursing" is
majors, not a request for Nursing's published facts, because the very
next thing that has to happen is asking THIS student for their GPA and
coursework. Also majors: a student giving their own GPA/prerequisite
courses/grades and asking about their own eligibility, or asking for help
choosing a major based on their interests. This is a stateful
conversation held across multiple messages -- GPA and courses may arrive
over several turns, not all at once, so a bare follow-up like "my GPA is
3.6" with no major named in that message is still majors if the
conversation so far was already headed there."""

CLASSIFY_TOOL = {
    "name": "classify_question",
    "description": (
        "Decide how to route a University of Memphis student's question: "
        "to a Tier-1 factual domain, to the personalized Majors advising "
        "flow, or as unclear/out of scope."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "route": {
                "type": "string",
                "enum": ["tier1", "majors", "unclear"],
                "description": (
                    "'tier1' for a factual question a single listed domain "
                    "covers. 'majors' for personalized major eligibility/"
                    "advising using the student's own numbers, or general "
                    "'help me pick a major' guidance. 'unclear' if the "
                    "question doesn't fit any listed domain or Majors."
                ),
            },
            "domain": {
                "type": ["string", "null"],
                "description": (
                    "Only when route is 'tier1': the single domain key this "
                    "question needs. Null otherwise."
                ),
            },
        },
        "required": ["route", "domain"],
    },
}

SYSTEM_TEMPLATE = """You classify a University of Memphis student's question
so it can be routed to the right system. Read the whole conversation so
far, not just the latest message -- a follow-up like "my GPA is 3.6" only
makes sense in light of what was already said.

Tier-1 domains (factual, not personalized):
{domain_descriptions}

Majors advising (personalized, stateful):
{majors_description}

A general question about a domain's own published facts (what does a
major require, what does a dorm cost, how do most students change their
major) is 'tier1'. Once the student expresses their own intent to apply
to, declare, or get into a specific major with its own eligibility
criteria -- or gives their own numbers, or wants help choosing -- it's
'majors', even on the very first message before any numbers are given. If
the question doesn't fit any listed domain and isn't about majors, route
'unclear' rather than forcing it into the closest domain."""


def _system_prompt() -> str:
    domains = load_domains()
    descriptions = "\n\n".join(
        f"- {name}: {config.prompt_snippet.strip()}"
        for name, config in domains.items()
    )
    return SYSTEM_TEMPLATE.format(
        domain_descriptions=descriptions, majors_description=MAJORS_DESCRIPTION
    )


UNCLEAR_ANSWER_TEMPLATE = (
    "I don't have data to answer that. I can help with: {topics}, and "
    "choosing or applying to a major."
)


def _unclear_answer() -> str:
    topics = ", ".join(load_domains().keys())
    return UNCLEAR_ANSWER_TEMPLATE.format(topics=topics)


def router(state: AppState) -> dict:
    """Classifies every turn from scratch against the full message history
    -- necessary so a bare follow-up in an ongoing Majors conversation
    ("my GPA is 3.6") still classifies as 'majors' rather than 'unclear',
    the same reason majors_intake re-derives from full history each turn.
    """
    response = _get_client().messages.create(
        model="claude-opus-5",
        max_tokens=300,
        system=_system_prompt(),
        tools=[CLASSIFY_TOOL],
        tool_choice={"type": "tool", "name": "classify_question"},
        messages=state["messages"],
    )
    classification = next(
        block.input for block in response.content if block.type == "tool_use"
    )

    route = classification["route"]
    domain = classification["domain"]

    result = {"route": route, "domain": domain}
    if route == "unclear":
        # Bypasses guardrails entirely (like majors_intake's "not ready"
        # path already does) -- guardrails.py looks up a domain config,
        # and there's no domain here to look up.
        result.update(
            {"answer": _unclear_answer(), "sources": [], "confidence_ok": False, "deferred": False}
        )
    return result
