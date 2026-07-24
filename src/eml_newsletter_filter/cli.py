import argparse
from pathlib import Path

from .classifier import classify_email
from .config import load_config
from .file_operations import copy_unique, eml_inputs
from .models import ClassificationResult
from .parser import parse_eml
from .report import write_reports


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Classify local .eml files as newsletters")
    subparsers = parser.add_subparsers(dest="command", required=True)
    classify = subparsers.add_parser("classify")
    classify.add_argument("--input", required=True, type=Path)
    classify.add_argument("--config", required=True, type=Path)
    classify.add_argument("--output", required=True, type=Path)
    classify.add_argument("--dry-run", action="store_true")
    return parser


def run_classify(input_path: Path, config_path: Path, output: Path, dry_run: bool) -> list[ClassificationResult]:
    config = load_config(config_path)
    results: list[ClassificationResult] = []
    for source in eml_inputs(input_path):
        try:
            result = classify_email(parse_eml(source), config)
            if not dry_run:
                target = copy_unique(source, output / result.classification)
                result.output_file = str(target)
        except Exception as exc:
            result = ClassificationResult(source_file=str(source), output_file=None, classification="parse_error",
                score=0, subject="", sender="", parse_error=f"{type(exc).__name__}: {exc}", reasons=["parse error"])
        results.append(result)
    write_reports(results, output)
    return results


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        results = run_classify(args.input, args.config, args.output, args.dry_run)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        return 2
    counts = {name: sum(result.classification == name for result in results)
              for name in ("newsletter", "suspected_newsletter", "not_newsletter")}
    errors = sum(result.parse_error is not None for result in results)
    print("Classification counts: " + ", ".join(f"{key}={value}" for key, value in counts.items()))
    print(f"Parse errors: {errors}")
    return 0
