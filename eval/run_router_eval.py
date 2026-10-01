"""Drive eval/router_scenarios.py against the real unified graph.

Usage:
  python -m eval.run_router_eval           # manual review (unchanged)
  python -m eval.run_router_eval --gate    # asserts each scenario's
                                            # "expected" dict, exits 1 on failure
"""
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

from app.graph.build_app import build_app_graph  # noqa: E402
from eval.router_scenarios import SCENARIOS  # noqa: E402


def _check_expected(result: dict, expected: dict) -> list[str]:
    """Structural assertions (route, active domains, deferred) -- these
    are state facts the router/synthesizer either got right or didn't, not
    prose to grade, so a plain equality check is both correct and free."""
    failures = []
    for key, want in expected.items():
        if key == "active_domains_set":
            got = sorted(result.get("active_domains") or [])
            if got != sorted(want):
                failures.append(f"active_domains: expected {sorted(want)}, got {got}")
            continue
        if key == "min_domain_results":
            got = len(result.get("domain_results") or [])
            if got < want:
                failures.append(f"domain_results: expected at least {want}, got {got}")
            continue
        got = result.get(key)
        if got != want:
            failures.append(f"{key}: expected {want!r}, got {got!r}")
    return failures


def run_scenario(graph, scenario: dict, gate: bool = False) -> bool:
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
