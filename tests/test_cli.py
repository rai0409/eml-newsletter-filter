import json
from pathlib import Path

import pytest

from eml_newsletter_filter.cli import main


def config_file(tmp_path: Path) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text("{}", encoding="utf-8")
    return path


def eml(path: Path, headers: str = "", body: str = "hello") -> None:
    path.write_text(f"From: sender@example.com\nSubject: test\n{headers}\n\n{body}", encoding="utf-8")


def test_bad_file_does_not_stop_other_files_and_reports_are_created(tmp_path):
    source = tmp_path / "in"; source.mkdir()
    eml(source / "good.eml", "List-Unsubscribe: <x>\nList-ID: <x>")
    (source / "bad.eml").write_bytes(b"not an email")
    output = tmp_path / "out"
    assert main(["classify", "--input", str(source), "--config", str(config_file(tmp_path)), "--output", str(output)]) == 0
    records = [json.loads(line) for line in (output / "reports/results.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(records) == 2 and any(item["parse_error"] for item in records)
    broken = next(item for item in records if item["parse_error"])
    assert broken["classification"] == "not_newsletter"
    assert broken["score"] == 0 and broken["output_file"] is None
    assert {item["classification"] for item in records} <= {"newsletter", "suspected_newsletter", "not_newsletter"}
    assert (output / "reports/results.csv").is_file()
    assert (output / "newsletter/good.eml").is_file()


def test_dry_run_does_not_copy(tmp_path):
    source = tmp_path / "mail.eml"; eml(source, "List-Unsubscribe: <x>\nList-ID: <x>")
    output = tmp_path / "out"
    assert main(["classify", "--input", str(source), "--config", str(config_file(tmp_path)), "--output", str(output), "--dry-run"]) == 0
    assert not (output / "newsletter").exists()
    assert (output / "reports/results.jsonl").is_file()


def test_same_name_is_not_overwritten(tmp_path):
    source = tmp_path / "in"; (source / "a").mkdir(parents=True); (source / "b").mkdir()
    eml(source / "a/same.eml", "List-Unsubscribe: <x>\nList-ID: <x>")
    eml(source / "b/same.eml", "List-Unsubscribe: <x>\nList-ID: <x>")
    output = tmp_path / "out"
    main(["classify", "--input", str(source), "--config", str(config_file(tmp_path)), "--output", str(output)])
    assert sorted(path.name for path in (output / "newsletter").iterdir()) == ["same.eml", "same_1.eml"]


def test_invalid_single_file_extension_returns_error(tmp_path):
    source = tmp_path / "mail.txt"; source.write_text("x", encoding="utf-8")
    assert main(["classify", "--input", str(source), "--config", str(config_file(tmp_path)), "--output", str(tmp_path / "out")]) == 2


def test_path_overlap_is_rejected_and_nested_output_is_not_reprocessed(tmp_path, capsys):
    source = tmp_path / "input"; source.mkdir()
    eml(source / "high.eml", "List-Unsubscribe: <x>\nList-ID: <x>")
    eml(source / "mid.eml", "List-ID: <x>")
    eml(source / "normal.eml")
    config = config_file(tmp_path)
    assert main(["classify", "--input", str(source), "--config", str(config), "--output", str(source)]) == 2
    assert "same" in capsys.readouterr().err
    output = source / "output"
    args = ["classify", "--input", str(source), "--config", str(config), "--output", str(output)]
    assert main(args) == 0
    first_records = (output / "reports/results.jsonl").read_text(encoding="utf-8").splitlines()
    first_copies = sorted(path.relative_to(output) for path in output.rglob("*.eml"))
    assert main(args) == 0
    assert len((output / "reports/results.jsonl").read_text(encoding="utf-8").splitlines()) == len(first_records) == 3
    assert sorted(path.relative_to(output) for path in output.rglob("*.eml")) == first_copies


def test_input_inside_output_is_rejected(tmp_path, capsys):
    output = tmp_path / "output"; source = output / "input"; source.mkdir(parents=True)
    eml(source / "mail.eml")
    assert main(["classify", "--input", str(source), "--config", str(config_file(tmp_path)), "--output", str(output)]) == 2
    assert "inside the output" in capsys.readouterr().err


@pytest.mark.parametrize("config_text", [
    "classification: invalid",
    "feature_weights:\n  list_id: bad",
    "classification:\n  newsletter_threshold: '60'",
    "classification:\n  newsletter_threshold: true",
    "classification:\n  add_keyword_score: -1",
    "classification:\n  many_links_threshold: -1",
    "classification:\n  newsletter_threshold: 30\n  suspected_threshold: 30",
    "feature_weights:\n  unknown: 1",
    "keywords:\n  add_as_newsletter: value",
    "keywords:\n  add_as_newsletter: [1]",
    "keywords:\n  add_as_newsletter: ['']",
    "classification: [",
])
def test_config_errors_stop_before_reports_or_copies(tmp_path, capsys, config_text):
    source = tmp_path / "mail.eml"; eml(source)
    config = tmp_path / "invalid.yaml"; config.write_text(config_text, encoding="utf-8")
    output = tmp_path / "out"
    assert main(["classify", "--input", str(source), "--config", str(config), "--output", str(output)]) == 2
    assert "Error:" in capsys.readouterr().err
    assert not output.exists()


def test_missing_config_stops_before_reports_or_copies(tmp_path, capsys):
    source = tmp_path / "mail.eml"; eml(source)
    output = tmp_path / "out"
    assert main(["classify", "--input", str(source), "--config", str(tmp_path / "missing.yaml"), "--output", str(output)]) == 2
    assert "does not exist" in capsys.readouterr().err
    assert not output.exists()


def test_cli_reports_keyword_priority(tmp_path):
    source = tmp_path / "mail.eml"; eml(source, body="FORCEYES EXCLUDE")
    config = tmp_path / "config.yaml"
    config.write_text("keywords:\n  force_newsletter: [FORCEYES]\n  exclude_from_newsletter: [EXCLUDE]", encoding="utf-8")
    output = tmp_path / "out"
    assert main(["classify", "--input", str(source), "--config", str(config), "--output", str(output)]) == 0
    record = json.loads((output / "reports/results.jsonl").read_text(encoding="utf-8"))
    assert record["classification"] == "newsletter"
    assert record["matched_force_keywords"] == ["FORCEYES"]
    assert record["matched_exclude_keywords"] == []
