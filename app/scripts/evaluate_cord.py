"""Evaluate structured extraction against the CORD held-out test split.

CORD provides receipt images plus human-verified OCR ground truth, but no
plain-text field. We reconstruct plain text from the annotated OCR lines so
we evaluate the *extraction* layer in isolation from our own OCR pipeline
(which is not yet wired into DocuGuard). See docs/data-contract.md.

CORD does not label supplier_name, document_number, or currency at all, and
every CORD document is a retail receipt (not one of our invoice / purchase
order / delivery note types). So this script reports three separate signals
instead of one misleading blended score:

  1. total accuracy   - the one field CORD genuinely lets us check.
  2. document_type accuracy - every CORD item should be classified "other".
  3. abstention accuracy - fields CORD has no ground truth for should come
     back null/0.0 confidence, not a hallucinated value.
"""

import argparse
import asyncio
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from datasets import load_dataset

from app.config import get_settings
from app.extraction.structured import DocumentFields, StructuredDocumentExtractor

DATASET_NAME = "naver-clova-ix/cord-v2"
REPORT_DIR = Path("docs/eval-reports")

# CORD ships train/validation/test. Per docs/data-contract.md, "never tune on
# the official test split": any prompt or config change must be measured on
# `validation` first. `test` is only for the final, held-out report and
# should be run rarely, after the configuration is frozen.


def reconstruct_text(ground_truth: dict) -> str:
    """Join CORD's human-verified OCR words back into line-ordered plain text."""
    lines = []
    for line in ground_truth.get("valid_line", []):
        words = [w["text"] for w in line.get("words", [])]
        if words:
            lines.append(" ".join(words))
    return "\n".join(lines)


def normalize_amount(value: str | None) -> str | None:
    if value is None:
        return None
    digits = re.sub(r"[^0-9]", "", value)
    return digits or None


# Buckets are wide because the model tends to cluster its confidence values
# (e.g. mostly 0.85/0.9/0.95/1.0) rather than spreading continuously; a
# calibration table with fine-grained buckets would mostly be empty.
CALIBRATION_BUCKETS = [
    (0.0, 0.7, "0.0-0.7"),
    (0.7, 0.9, "0.7-0.9"),
    (0.9, 1.0, "0.9-1.0 (exclusive)"),
    (1.0, 1.0, "1.0"),
]


def compute_calibration(samples: list[dict]) -> list[dict]:
    """A well-calibrated model's stated confidence should roughly equal its
    actual accuracy in that confidence range. E.g. predictions made at ~0.9
    confidence should be correct about 90% of the time. If a bucket's
    accuracy is far below its confidence range, the model is overconfident
    there; a reviewer threshold set from stated confidence alone would be
    unsafe without checking this."""
    table = []
    for low, high, label in CALIBRATION_BUCKETS:
        if low == high:
            bucket = [s for s in samples if s["confidence"] == low]
        else:
            bucket = [s for s in samples if low <= s["confidence"] < high]
        if not bucket:
            continue
        correct = sum(1 for s in bucket if s["correct"])
        table.append(
            {
                "confidence_range": label,
                "sample_count": len(bucket),
                "actual_accuracy": correct / len(bucket),
            }
        )
    return table


async def evaluate(limit: int, split: str, commit: str | None) -> dict:
    settings = get_settings()
    if settings.openai_api_key is None:
        raise RuntimeError("DOCUGUARD_OPENAI_API_KEY is required.")

    dataset = load_dataset(DATASET_NAME, split=split)
    sample_count = min(limit, len(dataset))

    extractor = StructuredDocumentExtractor(
        api_key=settings.openai_api_key.get_secret_value(),
        model=settings.extraction_model,
    )

    total_checked = 0
    total_correct = 0
    doc_type_correct = 0
    enrichment_fields_checked = 0
    enrichment_fields_found = 0
    supplier_name_flagged = 0
    supplier_name_flags: list[dict] = []
    calibration_samples: list[dict] = []
    failures: list[dict] = []

    for index in range(sample_count):
        row = dataset[index]
        ground_truth = json.loads(row["ground_truth"])["gt_parse"]
        text = reconstruct_text(json.loads(row["ground_truth"]))
        if not text.strip():
            continue

        fields: DocumentFields = await extractor.extract(document_text=text)

        # CORD documents are retail receipts, which our schema has no
        # dedicated category for. "invoice" is a defensible call for a
        # receipt (both are proof-of-purchase documents); "purchase_order"
        # and "delivery_note" are not, since receipts never represent an
        # order request or a delivery confirmation.
        if fields.document_type in ("other", "invoice"):
            doc_type_correct += 1
        else:
            failures.append(
                {
                    "index": index,
                    "field": "document_type",
                    "expected": "other or invoice",
                    "actual": fields.document_type,
                }
            )

        expected_total = normalize_amount(
            ground_truth.get("total", {}).get("total_price")
        )
        if expected_total is not None:
            total_checked += 1
            actual_total = normalize_amount(fields.total.value)
            is_correct = actual_total == expected_total
            calibration_samples.append(
                {"correct": is_correct, "confidence": fields.total.confidence}
            )
            if is_correct:
                total_correct += 1
            else:
                failures.append(
                    {
                        "index": index,
                        "field": "total",
                        "expected": expected_total,
                        "actual": actual_total,
                        "confidence": fields.total.confidence,
                    }
                )

        # currency / document_number: CORD has no ground truth here, so a
        # non-null value is not an error -- it may genuinely be printed on
        # the receipt. We only track how often the model finds something.
        for field_name in ("document_number", "currency"):
            enrichment_fields_checked += 1
            extracted = getattr(fields, field_name)
            if extracted.value is not None:
                enrichment_fields_found += 1

        # supplier_name: CORD has no ground truth either, but manual review
        # of early runs showed the model repeatedly confusing menu item
        # names with the supplier name. We can't score this against a
        # ground truth, so we flag every non-null value for human review
        # instead of silently counting it as correct or wrong.
        supplier_field = fields.supplier_name
        if supplier_field.value is not None:
            supplier_name_flagged += 1
            supplier_name_flags.append(
                {
                    "index": index,
                    "value": supplier_field.value,
                    "evidence": supplier_field.evidence,
                    "confidence": supplier_field.confidence,
                }
            )

    calibration = compute_calibration(calibration_samples)

    report = {
        "dataset": DATASET_NAME,
        "dataset_split": split,
        "sample_count": sample_count,
        "extraction_model": settings.extraction_model,
        "commit": commit or None,
        "generated_at": datetime.now(UTC).isoformat(),
        "metrics": {
            "total_accuracy": total_correct / total_checked if total_checked else None,
            "total_checked": total_checked,
            "document_type_accuracy": doc_type_correct / sample_count if sample_count else None,
            "enrichment_rate": (
                enrichment_fields_found / enrichment_fields_checked
                if enrichment_fields_checked
                else None
            ),
            "enrichment_note": (
                "document_number/currency: CORD has no ground truth for these "
                "fields, so a non-null value is not scored as correct or "
                "incorrect -- it may genuinely be printed on the receipt. "
                "This rate only shows how often the model reports finding one."
            ),
            "supplier_name_flagged_count": supplier_name_flagged,
            "supplier_name_flagged_rate": (
                supplier_name_flagged / sample_count if sample_count else None
            ),
            "supplier_name_note": (
                "CORD has no supplier_name ground truth either, but manual "
                "review of early runs showed the model repeatedly returning "
                "a menu item name instead of a supplier/store name. Every "
                "non-null supplier_name is flagged for human review below "
                "rather than scored, since we cannot auto-verify it."
            ),
            "total_confidence_calibration": calibration,
            "calibration_note": (
                "Confidence calibration is measured only for 'total', the "
                "only field with real ground truth. A well-calibrated model "
                "is correct about as often as its stated confidence within "
                "each bucket; see compute_calibration()'s docstring."
            ),
        },
        "limitations": [
            (
                "CORD only ground-truths 'total'; supplier_name, "
                "document_number, and currency have no ground truth at all "
                "in this dataset."
            ),
            (
                "CORD documents are retail receipts, not invoices/purchase "
                "orders/delivery notes; document_type is graded as correct "
                "for either 'other' or 'invoice', since our schema has no "
                "receipt category and a receipt is a defensible invoice call."
            ),
            (
                f"{settings.extraction_model} is a reasoning model and does "
                "not support the 'temperature' parameter, so run-to-run "
                "variance is expected even with identical inputs and no "
                "code changes. Compare reports across multiple runs before "
                "treating a metric change as caused by a code/prompt change."
            ),
            (
                "Text was reconstructed from CORD's annotated OCR words, "
                "not run through DocuGuard's own OCR pipeline (not yet "
                "integrated)."
            ),
        ],
        "failures": failures,
        "supplier_name_flags": supplier_name_flags,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument(
        "--split",
        choices=["validation", "test"],
        default="validation",
        help=(
            "validation: safe to run repeatedly while iterating on the "
            "prompt. test: the held-out set -- run only for a final, "
            "frozen-configuration report (see docs/data-contract.md)."
        ),
    )
    arguments = parser.parse_args()

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    ).stdout.strip() or None

    report = asyncio.run(evaluate(arguments.limit, arguments.split, commit))

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_path = REPORT_DIR / f"cord-{arguments.split}-{timestamp}.json"
    output_path.write_text(json.dumps(report, indent=2))

    print(json.dumps(report["metrics"], indent=2))
    print(f"\nfull report: {output_path}")


if __name__ == "__main__":
    main()
