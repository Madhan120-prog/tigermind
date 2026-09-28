import os
import re

import anthropic
from langgraph.types import interrupt

from app.config.competitive_majors import CompetitiveMajor, match_competitive_major
from app.graph.app_state import AppState
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


def _declare_path(target_major: str) -> dict:
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

    return {
        "recommendation": {
            "path": "declare",
            "major": target_major,
            "eligibility_band": None,
            "sources": sources,
        },
        "recommendation_confirmed": True,
        "answer": response.content[0].text,
        "sources": sources,
        # So the shared guardrails node can run the same confidence gate a
        # Tier-1 domain question gets -- this path retrieves too, and had
        # no gate on it at all before.
        "retrieved": hits,
    }


_GRADE_VALUE = {
    "A+": 4.3, "A": 4.0, "A-": 3.7,
    "B+": 3.3, "B": 3.0, "B-": 2.7,
    "C+": 2.3, "C": 2.0, "C-": 1.7,
    "D+": 1.3, "D": 1.0, "D-": 0.7,
    "F": 0.0,
}


def _normalize_code(code: str) -> str:
    return " ".join(code.upper().split())


def _grade_meets_minimum(grade: str | None, minimum: str) -> bool:
    if grade is None:
        return False
    student_value = _GRADE_VALUE.get(grade.strip().upper())
    min_value = _GRADE_VALUE.get(minimum.strip().upper())
    if student_value is None or min_value is None:
        return False
    return student_value >= min_value


def _classify_prereqs(major: CompetitiveMajor, completed_courses: list[dict]) -> dict[str, list[str]]:
    """Each required prerequisite lands in exactly one bucket. A
    requirement is a list of equivalent course codes (e.g. CHEM 1010 or
    CHEM 1110) -- matching any one of them satisfies it, so a student
    isn't penalized for taking the accepted alternative.

    in_progress is intentionally not "failed" or "missing": the source
    explicitly allows applying with a prerequisite still in progress, so
    an otherwise-strong record with one in-progress course is not a
    confirmed problem the way a below-minimum grade or an unreported
    requirement is.
    """
    reported = {_normalize_code(c["code"]): c for c in completed_courses}
    buckets: dict[str, list[str]] = {
        "verified": [], "in_progress": [], "failed": [], "missing": []
    }
    for group in major.required_prereqs:
        entry = None
        label = group[0]
        for code in group:
            candidate = reported.get(_normalize_code(code))
            if candidate is not None:
                entry, label = candidate, code
                break
        if entry is None:
            buckets["missing"].append(label)
        elif entry.get("status") == "in_progress":
            buckets["in_progress"].append(label)
        elif _grade_meets_minimum(entry.get("grade"), major.min_prereq_grade):
            buckets["verified"].append(label)
        else:
            buckets["failed"].append(label)
    return buckets


def _gpa_status(value: float | None, minimum: float, margin: float) -> str:
    """'clear_pass' / 'clear_fail' / 'unclear' -- unclear covers both an
    unknown value and one sitting inside the margin band around the
    cutoff, since neither can be safely called a pass."""
    if value is None:
        return "unclear"
    if value < minimum - margin:
        return "clear_fail"
    if value >= minimum + margin:
        return "clear_pass"
    return "unclear"


def _prereqs_status(prereqs: dict[str, list[str]]) -> str:
    if prereqs["failed"]:
        return "clear_fail"
    if prereqs["missing"]:
        return "unclear"
    return "clear_pass"  # every requirement verified or acceptably in progress


def _eligibility_band(
    major: CompetitiveMajor, gpa: float, prereq_gpa: float | None, completed_courses: list[dict]
) -> str:
    """Threshold-based, not a competitive ranking (confirmed directly
    against the source), so a clean numeric distance from each cutoff is
    the right model for "borderline" -- not an approximation of how a
    ranked applicant pool would be judged.

    Cumulative GPA, prerequisite-specific GPA, and prerequisite
    completion are three independent checks. A strong result on one
    never substitutes for an unclear or failing result on another -- a
    single collapsed GPA figure used as a stand-in for both thresholds
    previously let a strong cumulative GPA mask a weak prerequisite GPA.
    Any confirmed failure on any check makes the whole read
    clearly_ineligible; every check has to clearly pass before the whole
    read is clearly_eligible; anything else is borderline.
    """
    margin = major.borderline_margin
    prereqs = _classify_prereqs(major, completed_courses)
    statuses = [
        _gpa_status(gpa, major.cumulative_gpa_min, margin),
        _gpa_status(prereq_gpa, major.prereq_gpa_min, margin),
        _prereqs_status(prereqs),
    ]

    if "clear_fail" in statuses:
        return "clearly_ineligible"
    if all(status == "clear_pass" for status in statuses):
        return "clearly_eligible"
    return "borderline"


def _borderline_reason(
    major: CompetitiveMajor, gpa: float, prereq_gpa: float | None, prereqs: dict[str, list[str]]
) -> str:
    margin = major.borderline_margin
    parts = []
    if _gpa_status(gpa, major.cumulative_gpa_min, margin) == "unclear":
        parts.append(f"cumulative GPA {gpa} close to the {major.cumulative_gpa_min} minimum")
    if prereq_gpa is None:
        parts.append("prerequisite-specific GPA not yet known")
    elif _gpa_status(prereq_gpa, major.prereq_gpa_min, margin) == "unclear":
        parts.append(f"prerequisite GPA {prereq_gpa} close to the {major.prereq_gpa_min} minimum")
    if prereqs["failed"]:
        parts.append(f"a below-minimum grade in {', '.join(prereqs['failed'])}")
    if prereqs["missing"]:
        parts.append(f"{', '.join(prereqs['missing'])} not yet reported")
    return "; ".join(parts) if parts else "the numbers reported"


def _competitive_path(
    major: CompetitiveMajor, gpa: float, prereq_gpa: float | None, completed_courses: list[dict]
) -> dict:
    # Everything above the interrupt() call must be pure/deterministic:
    # LangGraph re-runs this entire function from the top on resume, so an
    # LLM call or any other side effect placed before interrupt() would
    # run twice and could produce a different draft than what the student
    # already saw and responded to. See build_app.py's docstring.
    band = _eligibility_band(major, gpa, prereq_gpa, completed_courses)
    prereqs = _classify_prereqs(major, completed_courses)
    recommendation = {
        "path": "apply",
        "major": major.display_name,
        "eligibility_band": band,
        "sources": [major.source_url],
    }

    if band == "borderline":
        decision = interrupt(
            {
                "draft": recommendation,
                "prompt": (
                    f"Your numbers are close to {major.display_name}'s "
                    f"requirements ({_borderline_reason(major, gpa, prereq_gpa, prereqs)}). "
                    "Want me to finalize this read, or would you rather work "
                    "on your numbers first?"
                ),
            }
        )
        # Free-text decline detection: a real reply is "no, let me improve
        # my numbers first," not a bare "no" -- matching only the exact
        # word would have silently treated that as confirmation, which is
        # the one failure mode that actually defeats the point of asking.
        recommendation_confirmed = not re.match(r"^\s*no\b", str(decision).strip(), re.I)
    else:
        recommendation_confirmed = True

    if band == "borderline" and not recommendation_confirmed:
        # Declining means hold off entirely -- showing the eligibility
        # verdict anyway after the student asked to wait would make the
        # interrupt() pure theater. No eligibility facts in this prompt on
        # purpose: there is nothing to soften if the model never sees them.
        response = _get_client().messages.create(
            model="claude-sonnet-4-5",
            max_tokens=200,
            system=(
                "A student asked you to hold off on finalizing an eligibility "
                "read so they can work on their numbers first. Acknowledge "
                "that warmly and briefly, and invite them to share updated "
                "GPA or coursework whenever they're ready. Do not state or "
                "imply any eligibility verdict."
            ),
            messages=[{"role": "user", "content": str(decision)}],
        )
        return {
            "recommendation": recommendation,
            "recommendation_confirmed": False,
            "answer": response.content[0].text,
        }

    required_display = ", ".join(
        group[0] if len(group) == 1 else f"{group[0]} (or {'/'.join(group[1:])})"
        for group in major.required_prereqs
    )

    facts = f"""Major: {major.display_name}
College: {major.college}
Cumulative GPA minimum: {major.cumulative_gpa_min}
Prerequisite GPA minimum: {major.prereq_gpa_min}
Minimum grade per prerequisite: {major.min_prereq_grade}
Required prerequisites: {required_display}
Prerequisites verified complete at/above the minimum grade: {', '.join(prereqs['verified']) or 'none'}
Prerequisites in progress (allowed at application time per policy, not a problem): {', '.join(prereqs['in_progress']) or 'none'}
Prerequisites completed below the minimum grade: {', '.join(prereqs['failed']) or 'none'}
Prerequisites not yet reported at all: {', '.join(prereqs['missing']) or 'none'}
Application deadlines: Fall {major.application_deadlines.get('fall')}, Spring {major.application_deadlines.get('spring')}
Source: {major.source_url}

Student's reported cumulative GPA: {gpa}
Student's reported prerequisite-specific GPA: {prereq_gpa if prereq_gpa is not None else 'not provided'}
Student's reported courses: {completed_courses}
Eligibility read: {band}
"""

    response = _get_client().messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        system=(
            f"Compose a clear, honest answer for a student asking about "
            f"applying to {major.display_name}, a real competitive UofM "
            "major described as a published GPA-threshold exception, not a "
            "ranked or competitive process -- never call it 'competitive' "
            "or imply applicants are ranked against each other. Use only "
            "the facts below -- including the exact college name given, "
            "never a paraphrased or remembered version of it -- and the "
            "specific prerequisite breakdown, not just the overall "
            "eligibility read. An in-progress prerequisite is normal and "
            "allowed, not a problem to flag as a concern. If any "
            "prerequisite is below the minimum grade or was never "
            "reported, name it specifically. If the eligibility read is "
            "clearly_ineligible, say so plainly -- never promise admission "
            "or soften it into false hope. If clearly_eligible, confirm "
            "they meet the stated criteria. State the real deadlines and "
            "cite the source.\n\nFACTS:\n" + facts
        ),
        messages=[
            {"role": "user", "content": f"Am I eligible to apply for {major.display_name}?"}
        ],
    )

    return {
        "recommendation": recommendation,
        "recommendation_confirmed": recommendation_confirmed,
        "answer": response.content[0].text,
        "sources": recommendation["sources"],
    }


def majors_recommend(state: AppState) -> dict:
    target_major = state["target_major"]
    competitive = match_competitive_major(target_major)

    if competitive is None:
        return _declare_path(target_major)
    return _competitive_path(
        competitive, state["gpa"], state.get("prereq_gpa"), state["completed_courses"]
    )
