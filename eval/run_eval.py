"""Run eval_set.csv questions through the graph and print results for review.

Usage: python -m eval.run_eval housing
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

from app.graph.build import build_graph  # noqa: E402

EVAL_CSV_PATH = Path(__file__).parent / "eval_set.csv"


def run_eval(domain: str) -> None:
    graph = build_graph()

    with open(EVAL_CSV_PATH) as f:
        rows = [r for r in csv.DictReader(f) if r["domain"] == domain]

    if not rows:
        print(f"No eval rows found for domain '{domain}'")
        return

    for row in rows:
        result = graph.invoke({"question": row["question"], "domain": domain})
        print(f"\nQ: {row['question']}")
        print(f"Expected: {row['expected_source_or_answer']}")
        print(f"Got:      {result['answer']}")
        print(f"Sources:  {result['sources']}")
        print(f"Confidence OK: {result['confidence_ok']}  Deferred: {result['deferred']}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m eval.run_eval <domain>")
        sys.exit(1)
    run_eval(sys.argv[1])
