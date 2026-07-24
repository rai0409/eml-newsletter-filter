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


def load_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Config file does not exist: {path}")
    with path.open(encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError("config.yaml must contain a mapping")
    config = deepcopy(DEFAULT_CONFIG)
    for section in ("classification", "feature_weights", "keywords"):
        values = loaded.get(section, {})
        if not isinstance(values, dict):
            raise ValueError(f"{section} must be a mapping")
        config[section].update(values)
    for key in config["keywords"]:
        if not isinstance(config["keywords"][key], list):
            raise ValueError(f"keywords.{key} must be a list")
    return config
