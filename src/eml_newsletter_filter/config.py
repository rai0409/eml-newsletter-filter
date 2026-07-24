from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG: dict[str, Any] = {
    "classification": {"newsletter_threshold": 60, "suspected_threshold": 30,
                       "add_keyword_score": 20, "add_keyword_score_per_match": 8,
                       "add_keyword_score_cap": 24, "many_links_threshold": 10,
                       "link_density_threshold": 8.0, "require_strong_evidence_for_newsletter": True},
    "feature_weights": {"list_unsubscribe": 40, "list_id": 30, "list_unsubscribe_post": 20,
                        "precedence_bulk": 25, "precedence_list": 25, "list_help": 5,
                        "list_archive": 5, "list_post": 5, "unsubscribe_text": 20,
                        "campaign_header": 15, "view_in_browser": 10,
                        "tracking_parameters": 5, "many_links": 5, "automated_sender": 5, "content_pattern": 20},
    "keywords": {"exclude_from_newsletter": [], "add_as_newsletter": [],
                 "force_newsletter": [], "force_not_newsletter": []},
    "group_caps": {"list_header_group": 50, "unsubscribe_group": 25,
                   "campaign_provider_group": 15, "marketing_structure_group": 15,
                   "sender_pattern_group": 10, "content_pattern_group": 25,
                   "protection_group": 60},
    "organization": {"internal_domains": []},
    "protection_keywords": {"security": {"subject": ["認証コード", "ワンタイムパスワード", "セキュリティ通知", "ログイン通知", "パスワード変更", "verification code", "one-time password"], "body": ["有効期限", "IPアドレス", "login attempt"]}, "transactional": {"subject": ["注文確認", "ご注文ありがとうございます", "発送しました", "請求書", "領収書", "決済完了", "予約確認", "order confirmation", "invoice", "receipt"], "body": ["注文番号", "請求番号", "配送番号", "予約番号", "合計金額"]}, "business_notification": {"subject": ["障害通知", "メンテナンス", "アラート", "承認依頼", "タスク通知", "system alert", "incident"], "body": []}},
    "keyword_matching": {"min_alphanumeric_length": 3, "allow_short_exact_tokens": []},
}

FEATURE_NAMES = frozenset(DEFAULT_CONFIG["feature_weights"])
KEYWORD_GROUPS = frozenset(DEFAULT_CONFIG["keywords"])
GROUP_CAPS = frozenset(DEFAULT_CONFIG["group_caps"])


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

def _require_number(value: Any, name: str) -> float:
    if type(value) not in (int, float) or value < 0 or value != value:
        raise ConfigError(f"{name} must be a non-negative number")
    return float(value)


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
    for section in ("classification", "feature_weights", "keywords", "group_caps", "organization", "protection_keywords", "keyword_matching"):
        values = _require_mapping(loaded.get(section, {}), section)
        config[section].update(values)

    unknown_features = set(config["feature_weights"]) - FEATURE_NAMES
    if unknown_features:
        raise ConfigError(f"Unknown feature weight(s): {', '.join(sorted(unknown_features))}")
    unknown_keyword_groups = set(config["keywords"]) - KEYWORD_GROUPS
    if unknown_keyword_groups:
        raise ConfigError(f"Unknown keyword group(s): {', '.join(sorted(unknown_keyword_groups))}")
    unknown_caps = set(config["group_caps"]) - GROUP_CAPS
    if unknown_caps:
        raise ConfigError(f"Unknown group cap(s): {', '.join(sorted(unknown_caps))}")

    classification = config["classification"]
    newsletter_threshold = _require_int(classification["newsletter_threshold"], "classification.newsletter_threshold")
    suspected_threshold = _require_int(classification["suspected_threshold"], "classification.suspected_threshold")
    if newsletter_threshold <= suspected_threshold:
        raise ConfigError("classification.newsletter_threshold must be greater than suspected_threshold")
    _require_non_negative_int(classification["add_keyword_score"], "classification.add_keyword_score")
    _require_non_negative_int(classification["many_links_threshold"], "classification.many_links_threshold")
    _require_non_negative_int(classification["add_keyword_score_per_match"], "classification.add_keyword_score_per_match")
    _require_non_negative_int(classification["add_keyword_score_cap"], "classification.add_keyword_score_cap")
    _require_number(classification["link_density_threshold"], "classification.link_density_threshold")
    if type(classification["require_strong_evidence_for_newsletter"]) is not bool:
        raise ConfigError("classification.require_strong_evidence_for_newsletter must be a boolean")

    for name, weight in config["feature_weights"].items():
        _require_int(weight, f"feature_weights.{name}")
    for name in KEYWORD_GROUPS:
        values = config["keywords"][name]
        if not isinstance(values, list):
            raise ConfigError(f"keywords.{name} must be a list")
        if any(not isinstance(value, str) or not value for value in values):
            raise ConfigError(f"keywords.{name} must contain non-empty strings only")
    for name, cap in config["group_caps"].items(): _require_non_negative_int(cap, f"group_caps.{name}")
    domains = config["organization"]["internal_domains"]
    if not isinstance(domains, list) or any(not isinstance(value, str) or not value for value in domains):
        raise ConfigError("organization.internal_domains must contain non-empty strings only")
    for category, fields in config["protection_keywords"].items():
        if not isinstance(fields, dict) or set(fields) - {"subject", "body"}:
            raise ConfigError(f"protection_keywords.{category} must contain subject/body lists")
        for field in ("subject", "body"):
            values = fields.get(field, [])
            if not isinstance(values, list) or any(not isinstance(value, str) or not value for value in values):
                raise ConfigError(f"protection_keywords.{category}.{field} must contain non-empty strings only")
    matching = config["keyword_matching"]
    _require_non_negative_int(matching["min_alphanumeric_length"], "keyword_matching.min_alphanumeric_length")
    if not isinstance(matching["allow_short_exact_tokens"], list) or any(not isinstance(v, str) or not v for v in matching["allow_short_exact_tokens"]):
        raise ConfigError("keyword_matching.allow_short_exact_tokens must contain non-empty strings only")
    return config
