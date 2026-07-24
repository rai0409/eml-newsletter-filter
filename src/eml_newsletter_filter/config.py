from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG: dict[str, Any] = {
    "classification": {"newsletter_threshold": 60, "suspected_threshold": 30,
                       "add_keyword_score": 20, "many_links_threshold": 10},
    "feature_weights": {"list_unsubscribe": 40, "list_id": 30, "list_unsubscribe_post": 20,
                        "precedence_bulk": 25, "precedence_list": 25, "list_help": 5,
                        "list_archive": 5, "list_post": 5, "unsubscribe_text": 20,
                        "campaign_header": 15, "view_in_browser": 10,
                        "tracking_parameters": 5, "many_links": 5, "automated_sender": 5},
    "keywords": {"exclude_from_newsletter": [], "add_as_newsletter": [],
                 "force_newsletter": [], "force_not_newsletter": []},
}

FEATURE_NAMES = frozenset(DEFAULT_CONFIG["feature_weights"])
KEYWORD_GROUPS = frozenset(DEFAULT_CONFIG["keywords"])


class ConfigError(ValueError):
    """Raised when a configuration cannot be safely used for classification."""


def _require_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{name} must be a mapping")
    return value


def _require_non_negative_int(value: Any, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ConfigError(f"{name} must be a non-negative integer")
    return value


def _require_int(value: Any, name: str) -> int:
    if type(value) is not int:
        raise ConfigError(f"{name} must be an integer")
    return value


def load_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"Config file does not exist: {path}")
    try:
        with path.open(encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML: {exc}") from exc
    loaded = _require_mapping(loaded, "config.yaml")
    config = deepcopy(DEFAULT_CONFIG)
    for section in ("classification", "feature_weights", "keywords"):
        values = _require_mapping(loaded.get(section, {}), section)
        config[section].update(values)

    unknown_features = set(config["feature_weights"]) - FEATURE_NAMES
    if unknown_features:
        raise ConfigError(f"Unknown feature weight(s): {', '.join(sorted(unknown_features))}")
    unknown_keyword_groups = set(config["keywords"]) - KEYWORD_GROUPS
    if unknown_keyword_groups:
        raise ConfigError(f"Unknown keyword group(s): {', '.join(sorted(unknown_keyword_groups))}")

    classification = config["classification"]
    newsletter_threshold = _require_int(classification["newsletter_threshold"], "classification.newsletter_threshold")
    suspected_threshold = _require_int(classification["suspected_threshold"], "classification.suspected_threshold")
    if newsletter_threshold <= suspected_threshold:
        raise ConfigError("classification.newsletter_threshold must be greater than suspected_threshold")
    _require_non_negative_int(classification["add_keyword_score"], "classification.add_keyword_score")
    _require_non_negative_int(classification["many_links_threshold"], "classification.many_links_threshold")

    for name, weight in config["feature_weights"].items():
        _require_int(weight, f"feature_weights.{name}")
    for name in KEYWORD_GROUPS:
        values = config["keywords"][name]
        if not isinstance(values, list):
            raise ConfigError(f"keywords.{name} must be a list")
        if any(not isinstance(value, str) or not value for value in values):
            raise ConfigError(f"keywords.{name} must contain non-empty strings only")
    return config
