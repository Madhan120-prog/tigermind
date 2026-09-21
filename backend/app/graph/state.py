from typing import TypedDict


class GraphState(TypedDict):
    question: str
    domain: str
    retrieved: list[dict]
    answer: str
    sources: list[str]
    confidence_ok: bool
    deferred: bool
