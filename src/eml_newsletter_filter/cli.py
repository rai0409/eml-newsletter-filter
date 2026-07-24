import argparse
import json
import sys
from pathlib import Path

from .classifier import classify_email
from .config import ConfigError, load_config
from .file_operations import copy_unique, eml_inputs, validate_input_output_paths
from .models import ClassificationResult
from .parser import parse_eml
from .report import write_reports
from .evaluation import evaluate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Classify local .eml files as newsletters")
    subparsers = parser.add_subparsers(dest="command", required=True)
    classify = subparsers.add_parser("classify")
    classify.add_argument("--input", required=True, type=Path)
    classify.add_argument("--config", required=True, type=Path)
    classify.add_argument("--output", required=True, type=Path)
    classify.add_argument("--dry-run", action="store_true")
    evaluate_parser = subparsers.add_parser("evaluate")
    evaluate_parser.add_argument("--manifest", required=True, type=Path)
    evaluate_parser.add_argument("--input", required=True, type=Path)
    evaluate_parser.add_argument("--config", required=True, type=Path)
    return parser


def _previous_output_files(output: Path) -> dict[str, Path]:
    report = output / "reports" / "results.jsonl"
    if not report.is_file():
        return {}
    try:
        with report.open(encoding="utf-8") as handle:
            records = (json.loads(line) for line in handle if line.strip())
            return {
                record["source_file"]: Path(record["output_file"])
                for record in records
                if record.get("output_file")
            }
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return {}


def _same_content(first: Path, second: Path) -> bool:
    return first.is_file() and second.is_file() and first.read_bytes() == second.read_bytes()


def run_classify(input_path: Path, config_path: Path, output: Path, dry_run: bool) -> list[ClassificationResult]:
    config = load_config(config_path)
    excluded_root = validate_input_output_paths(input_path, output)
    previous_outputs = _previous_output_files(output)
    results: list[ClassificationResult] = []
    for source in eml_inputs(input_path, excluded_root):
        try:
            result = classify_email(parse_eml(source), config)
            if not dry_run:
                previous = previous_outputs.get(str(source))
                destination_dir = output / result.classification
                target = previous if (
                    previous and previous.parent.resolve() == destination_dir.resolve()
                    and _same_content(source, previous)
                ) else copy_unique(source, destination_dir)
                result.output_file = str(target)
        except Exception as exc:
            result = ClassificationResult(source_file=str(source), output_file=None, classification="not_newsletter",
                score=0, subject="", sender="", parse_error=f"{type(exc).__name__}: {exc}", reasons=["parse error"])
        results.append(result)
    write_reports(results, output)
    return results


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "evaluate":
            summary = evaluate(args.manifest, args.input, load_config(args.config))
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0
        results = run_classify(args.input, args.config, args.output, args.dry_run)
    except (ConfigError, FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    counts = {name: sum(result.classification == name for result in results)
              for name in ("newsletter", "suspected_newsletter", "not_newsletter")}
    errors = sum(result.parse_error is not None for result in results)
    print("Classification counts: " + ", ".join(f"{key}={value}" for key, value in counts.items()))
    print(f"Parse errors: {errors}")
    return 0
