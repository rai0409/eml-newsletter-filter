import csv
import json
from dataclasses import asdict
from pathlib import Path

from .models import ClassificationResult


FIELDS = ["source_file", "output_file", "classification", "score", "subject", "sender",
          "matched_features", "matched_add_keywords", "matched_exclude_keywords",
          "matched_force_keywords", "reasons", "parse_error"]


def write_reports(results: list[ClassificationResult], output: Path) -> None:
    reports = output / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    records = [asdict(result) for result in results]
    with (reports / "results.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    with (reports / "results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for record in records:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, list) else value
                             for key, value in record.items()})
