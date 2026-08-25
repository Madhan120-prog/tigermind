import re

from app.config.loader import get_domain
from app.graph.state import GraphState

# Chroma L2 distance on normalized sentence-transformer embeddings.
# Starting value -- needs calibration against real eval results, not tuned yet.
CONFIDENCE_DISTANCE_THRESHOLD = 1.1

NO_CONFIDENT_ANSWER = "I couldn't find a confident answer to that in {domain}'s current data."

DOLLAR_OR_DATE_PATTERN = re.compile(r"\$\d|\b\d{1,2}/\d{1,2}\b|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\b")

FRESHNESS_DISCLAIMER = "\n\n(Note: please confirm this is still current -- this information can change semester to semester.)"

DEFERRAL_TEMPLATE = (
    "I'd rather point you to someone who can answer this authoritatively "
    "than answer it myself.\n\n{because}\n\nPlease contact {refer_to}"
)


def _triggered_deferral(question: str, deferrals: list[dict]) -> dict | None:
    """Match a question against a domain's configured deferral triggers.

    Keyword matching rather than an LLM classification on purpose: a
    guardrail that fires probabilistically is not a guardrail. The same
    question deferred on one run and answered with a fabricated figure on
    the next when this lived in the prompt alone -- which is what motivated
    moving it into code.

    Word-boundary matched so a trigger like "opt" cannot fire on "option".
    """
    lowered = question.lower()
    for deferral in deferrals:
        for trigger in deferral.get("triggers", []):
            if re.search(rf"\b{re.escape(trigger.lower())}\b", lowered):
                return deferral
    return None


def guardrails(state: GraphState) -> dict:
    domain_name = state["domain"]
    config = get_domain(domain_name)
    hits = state["retrieved"]
    answer = state["answer"]

    # Before confidence or freshness: if the question is one this domain must
    # not answer, retrieval quality is irrelevant. A confident, well-cited
    # answer is the dangerous outcome here, not the safe one.
    deferral = _triggered_deferral(state["question"], config.deferrals)
    if deferral is not None:
        return {
            "deferred": True,
            "confidence_ok": True,
            "answer": DEFERRAL_TEMPLATE.format(
                because=" ".join(deferral["because"].split()),
                refer_to=" ".join(deferral["refer_to"].split()),
            ),
            "sources": state["sources"],
        }

    best_distance = min((h["distance"] for h in hits), default=float("inf"))
    confidence_ok = best_distance <= CONFIDENCE_DISTANCE_THRESHOLD

    if not confidence_ok:
        return {
            "deferred": False,
            "confidence_ok": False,
            "answer": NO_CONFIDENT_ANSWER.format(domain=domain_name),
            "sources": [],
        }

    if not state["sources"]:
        return {
            "deferred": False,
            "confidence_ok": False,
            "answer": NO_CONFIDENT_ANSWER.format(domain=domain_name),
        }

    needs_disclaimer = config.freshness_tier == "fast" or DOLLAR_OR_DATE_PATTERN.search(answer)
    if needs_disclaimer:
        answer = answer + FRESHNESS_DISCLAIMER

    return {"deferred": False, "confidence_ok": True, "answer": answer}
