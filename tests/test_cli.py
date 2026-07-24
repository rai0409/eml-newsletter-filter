import json
from pathlib import Path

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
