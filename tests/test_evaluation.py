import csv
import json

from eml_newsletter_filter.cli import main


def test_evaluate_outputs_metrics_without_copying(tmp_path, capsys):
    mail_dir = tmp_path / "eml"; mail_dir.mkdir()
    templates = [("newsletter", "", "List-Unsubscribe: <x>\nList-ID: <x>"),
                 ("not_newsletter", "security", "Subject: 認証コード\nContent-Type: text/plain; charset=utf-8"),
                 ("suspected_newsletter", "", "List-ID: <x>")]
    cases = [(f"case_{index:02d}.eml", *templates[index % len(templates)]) for index in range(30)]
    for filename, _, _, headers in cases:
        (mail_dir / filename).write_text(f"From: x@example.com\n{headers}\n\nhello", encoding="utf-8")
    manifest = tmp_path / "manifest.csv"
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["filename", "expected_classification", "protected_type", "notes"])
        writer.writeheader()
        for filename, expected, protected, _ in cases: writer.writerow({"filename": filename, "expected_classification": expected, "protected_type": protected, "notes": "synthetic"})
    config = tmp_path / "config.yaml"; config.write_text("{}", encoding="utf-8")
    assert main(["evaluate", "--manifest", str(manifest), "--input", str(mail_dir), "--config", str(config)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["evaluated_count"] == 30 and result["protected_newsletter_false_positives"] == 0
    assert not list(mail_dir.glob("*.copy"))
