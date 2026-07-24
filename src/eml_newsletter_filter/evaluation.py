import csv
from pathlib import Path

from .classifier import classify_email
from .parser import parse_eml

CLASSES = ("newsletter", "suspected_newsletter", "not_newsletter")


def evaluate(manifest: Path, input_dir: Path, config: dict) -> dict:
    if not manifest.is_file() or not input_dir.is_dir():
        raise ValueError("Manifest and evaluation input directory must exist")
    with manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or set(rows[0]) < {"filename", "expected_classification", "protected_type", "notes"}:
        raise ValueError("Manifest must contain filename, expected_classification, protected_type, notes")
    matrix = {actual: {expected: 0 for expected in CLASSES} for actual in CLASSES}; mistakes = []; protected_fp = 0
    for row in rows:
        expected = row["expected_classification"]
        if expected not in CLASSES or not row["filename"]:
            raise ValueError("Manifest contains an invalid expected_classification or filename")
        result = classify_email(parse_eml(input_dir / row["filename"]), config)
        matrix[expected][result.classification] += 1
        if expected != result.classification: mistakes.append({"filename": row["filename"], "expected": expected, "actual": result.classification, "reason": result.decision_reason_code})
        if row["protected_type"] and result.classification == "newsletter": protected_fp += 1
    total = len(rows); correct = sum(matrix[value][value] for value in CLASSES)
    tp = matrix["newsletter"]["newsletter"]; predicted = sum(matrix[x]["newsletter"] for x in CLASSES); expected = sum(matrix["newsletter"].values())
    return {"evaluated_count": total, "correct_count": correct, "accuracy": correct / total, "confusion_matrix": matrix,
            "newsletter_precision": tp / predicted if predicted else 0.0, "newsletter_recall": tp / expected if expected else 0.0,
            "protected_newsletter_false_positives": protected_fp, "suspected_newsletter_rate": sum(matrix[x]["suspected_newsletter"] for x in CLASSES) / total, "misclassifications": mistakes}
