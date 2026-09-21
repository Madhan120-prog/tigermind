import os
import re

import anthropic
from langgraph.types import interrupt

from app.config.competitive_majors import CompetitiveMajor, match_competitive_major
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
    """Each required prerequisite lands in exactly one bucket -- verified
    (completed at or above the minimum grade), failed (completed below
    it), or pending (in progress, or never reported at all). Matching by
    normalized course code, not by counting entries: a student who
    reported enough unrelated or failing courses to hit the required
    count previously scored clearly_eligible on volume alone, which is
    the bug this replaces."""
    reported = {_normalize_code(c["code"]): c for c in completed_courses}
    buckets: dict[str, list[str]] = {"verified": [], "failed": [], "pending": []}
    for req in major.required_prereqs:
        entry = reported.get(_normalize_code(req))
        if entry is None or entry.get("status") == "in_progress":
            buckets["pending"].append(req)
        elif _grade_meets_minimum(entry.get("grade"), major.min_prereq_grade):
            buckets["verified"].append(req)
        else:
            buckets["failed"].append(req)
    return buckets


def _eligibility_band(major: CompetitiveMajor, gpa: float, completed_courses: list[dict]) -> str:
    """Threshold-based, not a competitive ranking (confirmed directly
    against the source), so a clean numeric distance from the cutoff is
    the right model for "borderline" -- not an approximation of how a
    ranked applicant pool would be judged.

    Simplification, documented rather than hidden: the state schema
    collects one GPA figure, not separate cumulative/prerequisite GPAs,
    so it's used as a proxy for both.
    """
    threshold = min(major.cumulative_gpa_min, major.prereq_gpa_min)
    margin = major.borderline_margin
    prereqs = _classify_prereqs(major, completed_courses)

    if gpa < threshold - margin:
        return "clearly_ineligible"
    if prereqs["failed"] or prereqs["pending"]:
        # GPA alone can look fine while a required prerequisite is a
        # confirmed fail or still unresolved (in progress, or never
        # reported) -- the real outcome isn't settled either way, so this
        # is never clearly_eligible just because enough courses were named.
        return "borderline"
    if gpa >= threshold + margin:
        return "clearly_eligible"
    return "borderline"


def _threshold_display(major: CompetitiveMajor) -> float:
    return min(major.cumulative_gpa_min, major.prereq_gpa_min)


def _borderline_reason(major: CompetitiveMajor, gpa: float, prereqs: dict[str, list[str]]) -> str:
    threshold = _threshold_display(major)
    margin = major.borderline_margin
    parts = []
    if threshold - margin <= gpa < threshold + margin:
        parts.append(f"GPA {gpa} vs. a {threshold} minimum (margin {margin})")
    if prereqs["failed"]:
        parts.append(f"a below-minimum grade in {', '.join(prereqs['failed'])}")
    if prereqs["pending"]:
        parts.append(f"{', '.join(prereqs['pending'])} not yet confirmed complete")
    return "; ".join(parts) if parts else "the numbers reported"


def _competitive_path(major: CompetitiveMajor, gpa: float, completed_courses: list[dict]) -> dict:
    # Everything above the interrupt() call must be pure/deterministic:
    # LangGraph re-runs this entire function from the top on resume, so an
    # LLM call or any other side effect placed before interrupt() would
    # run twice and could produce a different draft than what the student
    # already saw and responded to. See build_majors.py's docstring.
    band = _eligibility_band(major, gpa, completed_courses)
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
                    f"requirements ({_borderline_reason(major, gpa, prereqs)}). "
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

    facts = f"""Major: {major.display_name}
College: {major.college}
Cumulative GPA minimum: {major.cumulative_gpa_min}
Prerequisite GPA minimum: {major.prereq_gpa_min}
Minimum grade per prerequisite: {major.min_prereq_grade}
Required prerequisites: {', '.join(major.required_prereqs)}
Prerequisites verified complete at/above the minimum grade: {', '.join(prereqs['verified']) or 'none'}
Prerequisites completed below the minimum grade: {', '.join(prereqs['failed']) or 'none'}
Prerequisites in progress or not yet reported: {', '.join(prereqs['pending']) or 'none'}
Application deadlines: Fall {major.application_deadlines.get('fall')}, Spring {major.application_deadlines.get('spring')}
Source: {major.source_url}

Student's reported GPA: {gpa}
Student's reported courses: {completed_courses}
Eligibility read: {band}
"""

    response = _get_client().messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        system=(
            f"Compose a clear, honest answer for a student asking about "
            f"applying to {major.display_name}, a real competitive UofM "
            "major. Use only the facts below -- including the exact college "
            "name given, never a paraphrased or remembered version of it, "
            "and the specific prerequisite breakdown (verified/below "
            "minimum/pending), not just the overall eligibility read. If "
            "any prerequisite is below the minimum grade or still pending, "
            "name it specifically rather than giving a vague overall "
            "answer. If the eligibility read is clearly_ineligible, say so "
            "plainly -- never promise admission or soften it into false "
            "hope. If clearly_eligible, confirm they meet the stated "
            "criteria. State the real deadlines and cite the "
            "source.\n\nFACTS:\n" + facts
        ),
        messages=[
            {"role": "user", "content": f"Am I eligible to apply for {major.display_name}?"}
        ],
    )

    return {
        "recommendation": recommendation,
        "recommendation_confirmed": recommendation_confirmed,
        "answer": response.content[0].text,
    }


def majors_recommend(state: MajorsState) -> dict:
    target_major = state["target_major"]
    competitive = match_competitive_major(target_major)

    if competitive is None:
        return _declare_path(target_major)
    return _competitive_path(competitive, state["gpa"], state["completed_courses"])
