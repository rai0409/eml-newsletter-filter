from .features import detect_features, find_keywords
from .models import ClassificationResult, ParsedEmail


def classify_email(email: ParsedEmail, config: dict) -> ClassificationResult:
    keywords = config["keywords"]
    text = email.searchable_text
    force_not = find_keywords(text, keywords["force_not_newsletter"])
    force_yes = find_keywords(text, keywords["force_newsletter"])
    exclude = find_keywords(text, keywords["exclude_from_newsletter"])
    base = dict(source_file=str(email.source_file), output_file=None, subject=email.subject, sender=email.sender)
    if force_not:
        return ClassificationResult(classification="not_newsletter", score=0, matched_force_keywords=force_not,
            reasons=["force_not_newsletter keyword"], **base)
    if force_yes:
        return ClassificationResult(classification="newsletter", score=0, matched_force_keywords=force_yes,
            reasons=["force_newsletter keyword"], **base)
    if exclude:
        return ClassificationResult(classification="not_newsletter", score=0, matched_exclude_keywords=exclude,
            reasons=["exclude_from_newsletter keyword"], **base)
    features, reasons = detect_features(email, config["classification"]["many_links_threshold"])
    score = sum(config["feature_weights"].get(feature, 0) for feature in features)
    add_keywords = find_keywords(text, keywords["add_as_newsletter"])
    if add_keywords:
        score += config["classification"]["add_keyword_score"]
        reasons.append("add_as_newsletter keyword")
    if "list_unsubscribe" in features and ("list_id" in features or "unsubscribe_text" in features):
        classification = "newsletter"; reasons.append("strong feature combination")
    elif score >= config["classification"]["newsletter_threshold"]: classification = "newsletter"
    elif score >= config["classification"]["suspected_threshold"]: classification = "suspected_newsletter"
    else: classification = "not_newsletter"
    return ClassificationResult(classification=classification, score=score, matched_features=features,
        matched_add_keywords=add_keywords, reasons=reasons, **base)
