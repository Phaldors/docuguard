"""Compare two evaluation reports and fail if a tracked metric regressed.

Generic across DocuGuard's eval report types (evaluate_cord.py,
evaluate_policy_assistant.py, evaluate_extraction_robustness.py): every
report is JSON with a top-level "metrics" dict of numeric values, so this
only needs to know, for each metric name it checks, whether higher or
lower is better. A metric absent from either report, or present but null
in either, is skipped rather than gated -- a report legitimately omits
metrics that had no applicable samples (see e.g. evaluate_cord.py's
total_accuracy when no document in the sample had a checkable total).
"""

import argparse
import json
import sys
from pathlib import Path

# Metric name -> "higher" | "lower". Only metrics listed here are gated;
# a metric present in both reports but not listed here is not checked.
METRIC_DIRECTIONS = {
    "total_accuracy": "higher",
    "document_type_accuracy": "higher",
    "recall_at_12": "higher",
    "cited_expected_chunk_rate": "higher",
    "citation_support_rate": "higher",
    "abstention_rate": "higher",
    "injection_resistance_rate": "higher",
    "supplier_name_flagged_rate": "lower",
}


def check_regression(
    baseline: dict, candidate: dict, *, tolerance: float = 0.02
) -> list[str]:
    failures: list[str] = []
    baseline_metrics = baseline.get("metrics", {})
    candidate_metrics = candidate.get("metrics", {})

    for metric_name, direction in METRIC_DIRECTIONS.items():
        if metric_name not in baseline_metrics or metric_name not in candidate_metrics:
            continue

        baseline_value = baseline_metrics[metric_name]
        candidate_value = candidate_metrics[metric_name]
        if baseline_value is None or candidate_value is None:
            continue

        if direction == "higher" and candidate_value < baseline_value - tolerance:
            failures.append(
                f"{metric_name}: {baseline_value:.4f} -> {candidate_value:.4f} "
                f"(dropped {baseline_value - candidate_value:.4f}, "
                f"tolerance {tolerance})"
            )
        elif direction == "lower" and candidate_value > baseline_value + tolerance:
            failures.append(
                f"{metric_name}: {baseline_value:.4f} -> {candidate_value:.4f} "
                f"(rose {candidate_value - baseline_value:.4f}, "
                f"tolerance {tolerance})"
            )

    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path, help="Path to the earlier report.")
    parser.add_argument("candidate", type=Path, help="Path to the newer report.")
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.02,
        help="Allowed drift before a metric counts as regressed (default 0.02).",
    )
    arguments = parser.parse_args()

    baseline = json.loads(arguments.baseline.read_text())
    candidate = json.loads(arguments.candidate.read_text())

    failures = check_regression(baseline, candidate, tolerance=arguments.tolerance)

    if failures:
        print("REGRESSION DETECTED:")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)

    print("No regressions detected.")


if __name__ == "__main__":
    main()
