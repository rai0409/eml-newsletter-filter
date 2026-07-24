from pathlib import Path

from eml_newsletter_filter.classifier import classify_email
from eml_newsletter_filter.config import DEFAULT_CONFIG
from eml_newsletter_filter.parser import parse_eml


def classify(tmp_path: Path, headers: str = "", body: str = "hello", config=None):
    path = tmp_path / "message.eml"
    path.write_text(f"From: sender@example.com\nSubject: test\n{headers}\n\n{body}", encoding="utf-8")
    return classify_email(parse_eml(path), config or DEFAULT_CONFIG)


def test_list_unsubscribe_and_list_id_is_newsletter(tmp_path):
    result = classify(tmp_path, "List-Unsubscribe: <https://x>\nList-ID: <list.x>")
    assert result.classification == "newsletter"


def test_list_id_alone_is_not_forced_newsletter(tmp_path):
    result = classify(tmp_path, "List-ID: <list.x>")
    assert result.classification == "suspected_newsletter"


def test_unsubscribe_text_alone_is_not_forced_newsletter(tmp_path):
    result = classify(tmp_path, body="unsubscribe here")
    assert result.classification != "newsletter"


def test_strong_features_over_threshold_are_newsletter(tmp_path):
    result = classify(tmp_path, "Precedence: bulk\nList-ID: <x>\nX-Campaign-ID: x")
    assert result.score >= 60 and result.classification == "newsletter"


def test_middle_score_is_suspected(tmp_path):
    assert classify(tmp_path, "List-ID: <x>").classification == "suspected_newsletter"


def test_no_features_is_not_newsletter(tmp_path):
    assert classify(tmp_path).classification == "not_newsletter"


def test_force_not_has_highest_priority(tmp_path):
    config = {**DEFAULT_CONFIG, "keywords": {**DEFAULT_CONFIG["keywords"], "force_not_newsletter": ["BLOCK"], "force_newsletter": ["BLOCK"]}}
    assert classify(tmp_path, body="BLOCK", config=config).classification == "not_newsletter"


def test_force_newsletter_does_not_outrank_exclude(tmp_path):
    config = {**DEFAULT_CONFIG, "keywords": {**DEFAULT_CONFIG["keywords"], "force_newsletter": ["weekly"], "exclude_from_newsletter": ["order"]}}
    assert classify(tmp_path, body="weekly order", config=config).classification == "not_newsletter"


def test_exclude_is_not_newsletter(tmp_path):
    config = {**DEFAULT_CONFIG, "keywords": {**DEFAULT_CONFIG["keywords"], "exclude_from_newsletter": ["receipt"]}}
    assert classify(tmp_path, body="receipt", config=config).classification == "not_newsletter"


def test_add_keyword_uses_configured_score(tmp_path):
    config = {**DEFAULT_CONFIG, "classification": {**DEFAULT_CONFIG["classification"], "add_keyword_score": 17}, "keywords": {**DEFAULT_CONFIG["keywords"], "add_as_newsletter": ["weekly"]}}
    result = classify(tmp_path, body="weekly", config=config)
    assert result.score == 17 and result.classification == "not_newsletter"
