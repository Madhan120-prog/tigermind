"""Run eval_set.csv questions through the graph.

Usage:
  python -m eval.run_eval <domain>           # manual review (unchanged)
  python -m eval.run_eval <domain> --gate    # judged pass/fail, exits 1 on failure
  python -m eval.run_eval --all [--gate]     # every domain actually in domains.yaml

eval_set.csv also has rows for domains that were researched in Phase 0 but
never built (flyers, events, exams-deadlines, course-catalog -- cut at
Phase 2's checkpoint, still blocked per PLAN.md 17.5/17.12). --all skips
those explicitly rather than crashing on an unknown domain.
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

from app.config.loader import load_domains  # noqa: E402
from app.graph.build import build_graph  # noqa: E402
from eval.judge import judge  # noqa: E402

EVAL_CSV_PATH = Path(__file__).parent / "eval_set.csv"


def _rows_for(domain: str) -> list[dict]:
    with open(EVAL_CSV_PATH) as f:
        return [r for r in csv.DictReader(f) if r["domain"] == domain]


def run_eval(domain: str, graph=None, gate: bool = False) -> bool:
    """Returns True if every row passed (or gate=False, where there's
    nothing to fail). A failing row gets exactly one retry -- PLAN.md
    17.11 found answer wording varies slightly run to run, so one flaky
    judgment shouldn't redden the whole build, but a question that fails
    twice in a row is a real regression, not sampling noise."""
    graph = graph or build_graph()
    rows = _rows_for(domain)

    if not rows:
        print(f"No eval rows found for domain '{domain}'")
        return True

    all_passed = True
    for row in rows:
        result = graph.invoke({"question": row["question"], "domain": domain})
        print(f"\nQ: {row['question']}")
        print(f"Expected: {row['expected_source_or_answer']}")
        print(f"Got:      {result['answer']}")
        print(f"Sources:  {result['sources']}")
        print(f"Confidence OK: {result['confidence_ok']}  Deferred: {result['deferred']}")

        if not gate:
            continue

        verdict, reason = judge(row["question"], row["expected_source_or_answer"], result["answer"])
        if verdict == "fail":
            retry_result = graph.invoke({"question": row["question"], "domain": domain})
            retry_verdict, retry_reason = judge(
                row["question"], row["expected_source_or_answer"], retry_result["answer"]
            )
            if retry_verdict == "fail":
                all_passed = False
                print(f"FAIL (failed twice): {reason} | retry: {retry_reason}")
            else:
                print(f"PASS (on retry): {retry_reason}")
        else:
            print(f"PASS: {reason}")

    return all_passed


def run_all(gate: bool = False) -> bool:
    live_domains = set(load_domains().keys())
    csv_domains = {r["domain"] for r in csv.DictReader(open(EVAL_CSV_PATH))}

    skipped = sorted(csv_domains - live_domains)
    if skipped:
        print(f"Skipping eval_set.csv rows for domains not yet built: {skipped}")

    graph = build_graph()
    all_passed = True
    for domain in sorted(live_domains):
        print(f"\n{'=' * 20} {domain} {'=' * 20}")
        if not run_eval(domain, graph=graph, gate=gate):
            all_passed = False
    return all_passed


if __name__ == "__main__":
    args = sys.argv[1:]
    gate = "--gate" in args
    args = [a for a in args if a != "--gate"]

    if args == ["--all"]:
        passed = run_all(gate=gate)
    elif len(args) == 1:
        passed = run_eval(args[0], gate=gate)
    else:
        print("Usage: python -m eval.run_eval <domain> [--gate]  OR  python -m eval.run_eval --all [--gate]")
        sys.exit(1)

    if gate and not passed:
        sys.exit(1)
