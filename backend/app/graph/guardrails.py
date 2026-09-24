import re

from app.config.loader import get_domain
from app.graph.app_state import AppState

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


FIGURE_WINDOW_CHARS = 100

_URL_PATTERN = re.compile(r"https?://\S+")

# A referral is the behaviour this check wants, but an office's room and
# phone number are digits sitting right next to the topic name -- so the
# naive check flagged a textbook-correct "contact International Student
# Services in Brister Hall room 120 at 901.678.4271" as asserting a figure.
_CONTACT_PATTERN = re.compile(r"\d{3}[.\-\s]\d{3}[.\-\s]\d{4}|\broom\s+\d+\b", re.I)


def _asserts_figure_on_deferred_topic(answer: str, deferrals: list[dict]) -> dict | None:
    """Catch a deferred topic the question never raised but the answer did.

    Triggers are matched against the question, so a domestic-sounding
    question like "how many hours can I work" does not defer -- and the
    agent was reproducibly volunteering an invented F-1 break limit in the
    answer anyway, citation attached. A figure is the harmful part: naming
    the office is fine, stating a number is not.

    Windowed both directions and erring toward deferring: an unnecessary
    deferral is an inconvenience, a fabricated visa limit is a status
    violation. Source URLs and contact details are stripped first -- one of
    this domain's own URLs contains "international", and a referral names an
    office whose room and phone number are digits beside the topic word.
    """
    lowered = _CONTACT_PATTERN.sub(" ", _URL_PATTERN.sub(" ", answer)).lower()
    for deferral in deferrals:
        triggers = [trigger.lower() for trigger in deferral.get("triggers", [])]
        # Blank the trigger words out of the window before looking for a
        # digit: "f-1" and "f1" contain one, so a trigger would otherwise
        # match itself and defer any answer that merely named the topic.
        blanking = re.compile("|".join(re.escape(trigger) for trigger in triggers)) if triggers else None
        for trigger in triggers:
            for match in re.finditer(rf"\b{re.escape(trigger)}\b", lowered):
                start = max(0, match.start() - FIGURE_WINDOW_CHARS)
                window = lowered[start : match.end() + FIGURE_WINDOW_CHARS]
                if re.search(r"\d", blanking.sub(" ", window)):
                    return deferral
    return None


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


def check_domain(domain_name: str, question: str, hits: list[dict], answer: str, sources: list[str]) -> dict:
    """The actual per-domain guardrail: deferral trigger match, then the
    confidence gate. Runs once per active domain, before any multi-domain
    synthesis -- a low-confidence or deferred sub-answer must be settled
    here, not handed to a synthesizer that could smooth it into fluent,
    confident-sounding prose and launder exactly the kind of fabricated
    figure this check exists to catch.
    """
    config = get_domain(domain_name)

    deferral = _triggered_deferral(question, config.deferrals) or (
        _asserts_figure_on_deferred_topic(answer, config.deferrals)
    )
    if deferral is not None:
        return {
            "domain": domain_name,
            "deferred": True,
            "confidence_ok": True,
            "answer": DEFERRAL_TEMPLATE.format(
                because=" ".join(deferral["because"].split()),
                refer_to=" ".join(deferral["refer_to"].split()),
            ),
            "sources": sources,
        }

    best_distance = min((h["distance"] for h in hits), default=float("inf"))
    confidence_ok = best_distance <= CONFIDENCE_DISTANCE_THRESHOLD and bool(sources)

    if not confidence_ok:
        return {
            "domain": domain_name,
            "deferred": False,
            "confidence_ok": False,
            "answer": NO_CONFIDENT_ANSWER.format(domain=domain_name),
            "sources": [],
        }

    return {
        "domain": domain_name,
        "deferred": False,
        "confidence_ok": True,
        "answer": answer,
        "sources": sources,
    }


def domain_guardrail_check(state: AppState) -> dict:
    """Fan-out branch node: runs check_domain for this one Send'd domain
    and joins its result into the shared domain_results list."""
    checked = check_domain(
        state["domain"], state["question"], state["retrieved"], state["answer"], state["sources"]
    )
    return {"domain_results": [checked]}


def guardrails(state: AppState) -> dict:
    """Final node, reached whether one domain answered directly or several
    were merged by the synthesizer. Per-domain deferral/confidence checks
    already happened in domain_guardrail_check -- this node only
    aggregates across however many domains were involved, decides on and
    appends a single freshness disclaimer (never one per domain, so a
    synthesized answer doesn't repeat the same note two or three times),
    and does a final citation sanity check.
    """
    results = state["domain_results"]

    if len(results) == 1:
        answer, sources = results[0]["answer"], results[0]["sources"]
    else:
        answer, sources = state["answer"], state["sources"]

    confidence_ok = all(r["confidence_ok"] for r in results)
    deferred = any(r["deferred"] for r in results)

    # A confident answer with nothing to cite is a contradiction, not a
    # pass -- matches the single-domain path's own belt-and-suspenders
    # check before this node existed.
    if confidence_ok and not sources:
        confidence_ok = False

    if confidence_ok:
        # Based on the non-deferred domains only -- one domain deferring
        # doesn't mean a genuine dollar figure another domain stated in
        # the same synthesized answer stops needing its disclaimer.
        non_deferred_domains = {r["domain"] for r in results if not r["deferred"]}
        needs_disclaimer = any(
            get_domain(d).freshness_tier == "fast" for d in non_deferred_domains
        ) or DOLLAR_OR_DATE_PATTERN.search(answer)
        if needs_disclaimer:
            answer = answer + FRESHNESS_DISCLAIMER

    return {"answer": answer, "sources": sources, "confidence_ok": confidence_ok, "deferred": deferred}
