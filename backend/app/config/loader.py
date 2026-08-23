from dataclasses import dataclass
from pathlib import Path

import yaml

DOMAINS_YAML_PATH = Path(__file__).parent / "domains.yaml"


@dataclass
class DomainConfig:
    name: str
    collection: str
    retrieval_mode: str
    freshness_tier: str
    prompt_snippet: str
    sources: list[str]


def load_domains() -> dict[str, DomainConfig]:
    raw = yaml.safe_load(DOMAINS_YAML_PATH.read_text())
    return {
        name: DomainConfig(name=name, **fields)
        for name, fields in raw.items()
    }


def get_domain(name: str) -> DomainConfig:
    domains = load_domains()
    if name not in domains:
        raise KeyError(
            f"Unknown domain '{name}'. Known domains: {sorted(domains)}"
        )
    return domains[name]
