from dataclasses import dataclass, field
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).parent / "competitive_majors.yaml"


@dataclass
class CompetitiveMajor:
    key: str
    display_name: str
    college: str
    aliases: list[str]
    cumulative_gpa_min: float
    prereq_gpa_min: float
    min_prereq_grade: str
    borderline_margin: float
    # Each entry is a list of equivalent course codes that all satisfy that
    # one requirement (e.g. ["CHEM 1010", "CHEM 1110"]) -- most lists have
    # exactly one code, but treating every requirement as a group avoids a
    # separate single-vs-equivalent code path in the matcher.
    required_prereqs: list[list[str]]
    application_deadlines: dict = field(default_factory=dict)
    source_url: str = ""
    notes: str = ""


def load_competitive_majors() -> dict[str, CompetitiveMajor]:
    raw = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    return {key: CompetitiveMajor(key=key, **fields) for key, fields in raw.items()}


def match_competitive_major(target_major: str | None) -> CompetitiveMajor | None:
    """A student names a major in free text ("Nursing", "the BSN program"),
    not a config key -- match against each entry's aliases rather than
    requiring an exact key match."""
    if not target_major:
        return None
    lowered = target_major.lower()
    for major in load_competitive_majors().values():
        if any(alias in lowered for alias in major.aliases):
            return major
    return None
