"""Drive eval/majors_scenarios.py against the real Majors graph directly
(bypassing the HTTP API -- cheaper, and this project hasn't settled an
automated pass/fail criterion yet, PLAN.md 17.7, so this prints actual
results for manual review, exactly like eval/run_eval.py does for the
Tier-1 domains).

Usage: python -m eval.run_majors_eval
"""
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

from langgraph.types import Command  # noqa: E402

from app.graph.build_majors import build_majors_graph  # noqa: E402
from eval.majors_scenarios import SCENARIOS  # noqa: E402


def run_scenario(graph, scenario: dict) -> None:
    print(f"\n=== {scenario['name']} ===")
    print(f"Checking: {scenario['checks']}")
    config = {"configurable": {"thread_id": uuid4().hex}}

    result = {}
    for turn in scenario["turns"]:
        if turn["kind"] == "message":
            result = graph.invoke(
                {"messages": [{"role": "user", "content": turn["content"]}]}, config
            )
        else:
            result = graph.invoke(Command(resume=turn["content"]), config)

        interrupted = "__interrupt__" in result
        band = (result.get("recommendation") or {}).get("eligibility_band")
        print(f"\n  turn ({turn['kind']}): {turn['content'][:70]!r}")
        print(
            f"    ready_to_recommend={result.get('ready_to_recommend')} "
            f"interrupted={interrupted} band={band}"
        )
        print(
            f"    target_major={result.get('target_major')!r} "
            f"interests={result.get('interests')} gpa={result.get('gpa')}"
        )
        if result.get("answer"):
            print(f"    answer: {result['answer'][:250]}")

    print(f"\n  final recommendation_confirmed={result.get('recommendation_confirmed')}")


if __name__ == "__main__":
    graph = build_majors_graph()
    for scenario in SCENARIOS:
        run_scenario(graph, scenario)
