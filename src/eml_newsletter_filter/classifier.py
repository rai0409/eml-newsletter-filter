from .features import detect_features, find_keywords, keyword_locations, link_metrics, normalize
from .models import ClassificationResult, ParsedEmail


def classify_email(email: ParsedEmail, config: dict) -> ClassificationResult:
    keywords = config["keywords"]
    matching = config["keyword_matching"]
    text = email.searchable_text
    finder = lambda values: find_keywords(text, values, matching["min_alphanumeric_length"], matching["allow_short_exact_tokens"])
    force_not, force_yes, exclude = finder(keywords["force_not_newsletter"]), finder(keywords["force_newsletter"]), finder(keywords["exclude_from_newsletter"])
    base = dict(source_file=str(email.source_file), output_file=None, subject=email.subject, sender=email.sender)
    if force_not:
        return ClassificationResult(classification="not_newsletter", score=0, matched_force_keywords=force_not,
            reasons=["force_not_newsletter keyword"], decision_reason_code="forced_not_newsletter", **base)
    if force_yes:
        return ClassificationResult(classification="newsletter", score=0, matched_force_keywords=force_yes,
            reasons=["force_newsletter keyword"], strong_newsletter_evidence=["force_newsletter"], decision_reason_code="forced_newsletter", **base)
    features, reasons = detect_features(email, config["classification"]["many_links_threshold"])
    groups = {"list_header_group": {"list_unsubscribe", "list_id", "list_unsubscribe_post", "precedence_bulk", "precedence_list", "list_help", "list_archive", "list_post"},
              "unsubscribe_group": {"unsubscribe_text", "view_in_browser"}, "campaign_provider_group": {"campaign_header"},
              "marketing_structure_group": {"tracking_parameters", "many_links"}, "sender_pattern_group": {"automated_sender"}}
    explicit = keyword_locations(email, ["ニュースレター", "メールマガジン", "メルマガ", "weekly newsletter", "今週のまとめ"], matching)
    if explicit: features.append("content_pattern"); reasons.append("newsletter content expression")
    groups["content_pattern_group"] = {"content_pattern"}
    raw_groups = {name: sum(config["feature_weights"].get(feature, 0) for feature in features if feature in members) for name, members in groups.items()}
    capped = {name: min(score, config["group_caps"][name]) for name, score in raw_groups.items()}
    metrics = link_metrics(email)
    if metrics["links_per_1000_characters"] >= config["classification"]["link_density_threshold"]:
        capped["marketing_structure_group"] = min(config["group_caps"]["marketing_structure_group"], capped["marketing_structure_group"] + 5)
    add_keywords = finder(keywords["add_as_newsletter"])
    add_score = min(len(add_keywords) * config["classification"]["add_keyword_score_per_match"], config["classification"]["add_keyword_score_cap"])
    # Legacy setting remains the one-time score only when new controls remain defaults and a legacy value is explicitly changed.
    if add_keywords and config["classification"]["add_keyword_score"] != 20 and config["classification"]["add_keyword_score_per_match"] == 8:
        add_score = config["classification"]["add_keyword_score"]
    if add_keywords: reasons.append("add_as_newsletter keyword")
    protection_hits: dict[str, dict[str, list[str]]] = {}; protection_score = 0; strong_protection = []
    for category, fields in config["protection_keywords"].items():
        subject_hits = find_keywords(email.subject, fields["subject"], matching["min_alphanumeric_length"], matching["allow_short_exact_tokens"])
        body_hits = find_keywords(email.plain_text + "\n" + email.html_text, fields["body"], matching["min_alphanumeric_length"], matching["allow_short_exact_tokens"])
        if subject_hits or body_hits:
            protection_hits[category] = {"subject": subject_hits, "body": body_hits}; protection_score += 20 if subject_hits else 8
            if (category == "security" and (subject_hits or body_hits)) or (subject_hits and body_hits): strong_protection.append(category)
    sender_domain = email.sender_address.rsplit("@", 1)[-1].casefold()
    internal = [normalize(d) for d in config["organization"]["internal_domains"]]
    is_internal = lambda domain: any(domain == value or domain.endswith("." + value) for value in internal)
    recipients_internal = [address for address in email.recipient_addresses if is_internal(address.rsplit("@", 1)[-1].casefold())]
    conversation = bool(email.headers.get("in-reply-to") or email.headers.get("references")) or bool(__import__("re").match(r"^(re|fw|fwd|返信|転送)\s*:", email.subject, __import__("re").I))
    if conversation: protection_score += 10
    if is_internal(sender_domain) and recipients_internal and "list_id" not in features: protection_score += 15
    if conversation and is_internal(sender_domain) and recipients_internal and "list_id" not in features: strong_protection.append("internal_conversation")
    protection_score = min(protection_score, config["group_caps"]["protection_group"])
    strong_newsletter = []
    if "list_unsubscribe" in features and "list_id" in features: strong_newsletter.append("list_unsubscribe_and_list_id")
    if "list_unsubscribe" in features and "unsubscribe_text" in features: strong_newsletter.append("list_unsubscribe_and_unsubscribe_text")
    if "list_id" in features and ({"precedence_bulk", "precedence_list"} & set(features)): strong_newsletter.append("list_id_and_precedence")
    if explicit and "unsubscribe_text" in features: strong_newsletter.append("content_and_unsubscribe")
    raw_score = sum(raw_groups.values()) + add_score; final_score = raw_score - protection_score
    if strong_protection and ("security" in strong_protection or "transactional" in strong_protection): classification, code = "not_newsletter", "strong_security_protection"
    elif exclude:
        classification, code, final_score = "not_newsletter", "excluded_keyword", 0
    elif strong_newsletter and final_score >= config["classification"]["newsletter_threshold"]:
        classification, code = ("suspected_newsletter", "conflicting_evidence") if strong_protection or protection_score >= 20 else ("newsletter", "strong_newsletter_evidence")
    elif final_score >= config["classification"]["newsletter_threshold"] and config["classification"]["require_strong_evidence_for_newsletter"]:
        classification, code = "suspected_newsletter", "insufficient_newsletter_evidence"
    elif final_score >= config["classification"]["suspected_threshold"]: classification, code = "suspected_newsletter", "score_suspected"
    else: classification, code = "not_newsletter", "insufficient_newsletter_evidence"
    return ClassificationResult(classification=classification, score=final_score, raw_newsletter_score=raw_score, protection_score=protection_score, final_score=final_score, group_scores={name: {"raw": raw_groups[name], "capped": capped[name]} for name in groups}, matched_features=features, matched_add_keywords=add_keywords, matched_exclude_keywords=exclude, matched_protection_keywords=protection_hits, matched_keyword_locations={**keyword_locations(email, add_keywords, matching), **({"content": sum(explicit.values(), [])} if explicit else {})}, link_metrics=metrics, strong_newsletter_evidence=strong_newsletter, strong_protection_evidence=strong_protection, reasons=reasons, decision_reason_code=code, **base)
