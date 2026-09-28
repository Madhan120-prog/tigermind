"""Drive eval/router_scenarios.py against the real unified graph, printing
actual results for manual review -- no automated pass/fail criterion
exists yet (PLAN.md 17.7), same as eval/run_eval.py and
eval/run_majors_eval.py.

Usage: python -m eval.run_router_eval
"""
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

from app.graph.build_app import build_app_graph  # noqa: E402
from eval.router_scenarios import SCENARIOS  # noqa: E402


def run_scenario(graph, scenario: dict) -> None:
    print(f"\n=== {scenario['name']} ===")
    print(f"Checking: {scenario['checks']}")

    config = {"configurable": {"thread_id": uuid4().hex}}
    result = graph.invoke(
        {"messages": [{"role": "user", "content": scenario["question"]}], "question": scenario["question"]},
        config,
    )

    print(f"  question: {scenario['question']!r}")
    print(f"  route={result.get('route')} active_domains={result.get('active_domains')}")
    if result.get("domain_results"):
        print(
            "  domain_results:",
            [(r["domain"], r["confidence_ok"], r["deferred"]) for r in result["domain_results"]],
        )
    print(f"  confidence_ok={result.get('confidence_ok')} deferred={result.get('deferred')}")
    print(f"  sources: {result.get('sources')}")
    print(f"  answer: {result.get('answer')}")


if __name__ == "__main__":
    graph = build_app_graph()
    for scenario in SCENARIOS:
        run_scenario(graph, scenario)
