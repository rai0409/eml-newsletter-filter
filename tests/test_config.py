import pytest

from eml_newsletter_filter.config import ConfigError, load_config


@pytest.mark.parametrize("content, message", [
    ("classification: invalid", "classification must be a mapping"),
    ("classification:\n  newsletter_threshold: '60'", "newsletter_threshold must be an integer"),
    ("classification:\n  newsletter_threshold: true", "newsletter_threshold must be an integer"),
    ("classification:\n  add_keyword_score: -1", "add_keyword_score must be a non-negative integer"),
    ("classification:\n  many_links_threshold: -1", "many_links_threshold must be a non-negative integer"),
    ("classification:\n  newsletter_threshold: 30\n  suspected_threshold: 30", "must be greater"),
    ("feature_weights:\n  unknown: 1", "Unknown feature weight"),
    ("keywords:\n  add_as_newsletter: value", "must be a list"),
    ("keywords:\n  add_as_newsletter: [1]", "non-empty strings"),
    ("keywords:\n  add_as_newsletter: ['']", "non-empty strings"),
    ("classification: [", "Invalid YAML"),
])
def test_invalid_config_is_rejected(tmp_path, content, message):
    path = tmp_path / "config.yaml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ConfigError, match=message):
        load_config(path)


def test_missing_config_is_rejected(tmp_path):
    with pytest.raises(ConfigError, match="does not exist"):
        load_config(tmp_path / "missing.yaml")
