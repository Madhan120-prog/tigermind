import re

from app.config.loader import get_domain
from app.graph.state import GraphState

# Chroma L2 distance on normalized sentence-transformer embeddings.
# Starting value -- needs calibration against real eval results, not tuned yet.
CONFIDENCE_DISTANCE_THRESHOLD = 1.1

NO_CONFIDENT_ANSWER = "I couldn't find a confident answer to that in {domain}'s current data."

DOLLAR_OR_DATE_PATTERN = re.compile(r"\$\d|\b\d{1,2}/\d{1,2}\b|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\b")

FRESHNESS_DISCLAIMER = "\n\n(Note: please confirm this is still current -- this information can change semester to semester.)"


def guardrails(state: GraphState) -> dict:
    domain_name = state["domain"]
    config = get_domain(domain_name)
    hits = state["retrieved"]
    answer = state["answer"]

    best_distance = min((h["distance"] for h in hits), default=float("inf"))
    confidence_ok = best_distance <= CONFIDENCE_DISTANCE_THRESHOLD

    if not confidence_ok:
        return {
            "confidence_ok": False,
            "answer": NO_CONFIDENT_ANSWER.format(domain=domain_name),
            "sources": [],
        }

    if not state["sources"]:
        return {
            "confidence_ok": False,
            "answer": NO_CONFIDENT_ANSWER.format(domain=domain_name),
        }

    needs_disclaimer = config.freshness_tier == "fast" or DOLLAR_OR_DATE_PATTERN.search(answer)
    if needs_disclaimer:
        answer = answer + FRESHNESS_DISCLAIMER

    return {"confidence_ok": True, "answer": answer}
