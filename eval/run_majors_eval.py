"""Drive eval/majors_scenarios.py against the real unified graph directly
(bypassing the HTTP API -- cheaper).

As of Phase 4, these scenarios go through the same router-driven graph as
every other question -- there's no more Majors-only entry point -- so this
also doubles as a check that the router keeps sending a Majors-flavored
conversation to majors_intake on every turn, not just the first.

Usage:
  python -m eval.run_majors_eval           # manual review (unchanged)
  python -m eval.run_majors_eval --gate    # asserts each scenario's
                                            # "expected" dict, exits 1 on failure
"""
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

from langgraph.types import Command  # noqa: E402

from app.graph.build_app import build_app_graph  # noqa: E402
from eval.majors_scenarios import SCENARIOS  # noqa: E402


def _check_expected(result: dict, expected: dict) -> list[str]:
    """Each scenario's expected outcome is a structural state assertion
    (route, band, interrupted, confirmed) already described in its prose
    "checks" field -- not prose to compare, so a plain equality check is
    both correct and free, no LLM judge needed."""
    failures = []
    for key, want in expected.items():
        if key == "min_interests":
            got = len(result.get("interests") or [])
            if got < want:
                failures.append(f"interests: expected at least {want}, got {got}")
            continue
        if key == "interrupted":
            got = "__interrupt__" in result
        elif key == "band":
            got = (result.get("recommendation") or {}).get("eligibility_band")
        else:
            got = result.get(key)
        if got != want:
            failures.append(f"{key}: expected {want!r}, got {got!r}")
    return failures


def run_scenario(graph, scenario: dict, gate: bool = False) -> bool:
    print(f"\n=== {scenario['name']} ===")
    print(f"Checking: {scenario['checks']}")
    config = {"configurable": {"thread_id": uuid4().hex}}

    result = {}
    for turn in scenario["turns"]:
        if turn["kind"] == "message":
            result = graph.invoke(
                {"messages": [{"role": "user", "content": turn["content"]}], "question": turn["content"]},
                config,
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

    if not gate:
        return True

    failures = _check_expected(result, scenario.get("expected", {}))
    if failures:
        print(f"  FAIL: {'; '.join(failures)}")
        return False
    print("  PASS")
    return True


if __name__ == "__main__":
    gate = "--gate" in sys.argv[1:]
    graph = build_app_graph()
    all_passed = True
    for scenario in SCENARIOS:
        if not run_scenario(graph, scenario, gate=gate):
            all_passed = False

    if gate and not all_passed:
        sys.exit(1)
