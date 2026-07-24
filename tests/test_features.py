from pathlib import Path

from eml_newsletter_filter.features import detect_features
from eml_newsletter_filter.parser import parse_eml


def test_detects_list_and_campaign_features(tmp_path: Path):
    path = tmp_path / "mail.eml"
    path.write_text("From: no-reply@example.com\nList-Unsubscribe: <https://x>\nList-ID: <list.x>\nX-MC-User: x\n\nunsubscribe", encoding="utf-8")
    features, _ = detect_features(parse_eml(path), 10)
    assert {"list_unsubscribe", "list_id", "campaign_header", "unsubscribe_text", "automated_sender"} <= set(features)
