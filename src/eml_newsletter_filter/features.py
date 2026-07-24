import re
import unicodedata
from urllib.parse import parse_qs, urlparse

from .models import ParsedEmail


def normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def find_keywords(text: str, keywords: list[str], min_alphanumeric_length: int = 3,
                  allow_short_exact_tokens: list[str] | None = None) -> list[str]:
    normalized = normalize(text); allowed = {normalize(value) for value in (allow_short_exact_tokens or [])}
    matched = []
    for keyword in keywords:
        value = normalize(keyword)
        if value.isascii() and value.replace(" ", "").isalnum():
            if len(value) < min_alphanumeric_length and value not in allowed:
                continue
            if re.search(rf"(?<![a-z0-9]){re.escape(value)}(?![a-z0-9])", normalized): matched.append(keyword)
        elif value in normalized: matched.append(keyword)
    return matched


def link_metrics(email: ParsedEmail) -> dict:
    domains = set(); utm = 0
    for href in email.html_links:
        parsed = urlparse(href)
        if parsed.hostname: domains.add(parsed.hostname.casefold())
        query = parse_qs(parsed.query)
        if any(key in query for key in ("utm_source", "utm_medium", "utm_campaign")): utm += 1
    visible = len((email.plain_text + "\n" + email.html_text).strip())
    return {"total_links": email.html_link_count, "utm_links": utm, "unique_link_domains": len(domains),
            "visible_text_characters": visible, "links_per_1000_characters": round(email.html_link_count * 1000 / max(visible, 1), 2),
            "has_html": bool(email.html_raw)}


def detect_features(email: ParsedEmail, many_links_threshold: int) -> tuple[list[str], list[str]]:
    headers = email.headers
    names = set(headers)
    features: list[str] = []
    reasons: list[str] = []
    def add(feature: str, reason: str) -> None:
        features.append(feature); reasons.append(reason)
    if "list-unsubscribe" in names: add("list_unsubscribe", "List-Unsubscribe header")
    if "list-id" in names: add("list_id", "List-ID header")
    if "list-unsubscribe-post" in names: add("list_unsubscribe_post", "List-Unsubscribe-Post header")
    if "list-help" in names: add("list_help", "List-Help header")
    if "list-archive" in names: add("list_archive", "List-Archive header")
    if "list-post" in names: add("list_post", "List-Post header")
    precedence = normalize(" ".join(headers.get("precedence", [])))
    if re.search(r"\bbulk\b", precedence): add("precedence_bulk", "Precedence: bulk")
    if re.search(r"\blist\b", precedence): add("precedence_list", "Precedence: list")
    if any(name.startswith(prefix) for name in names for prefix in
           ("x-mailchimp-", "x-mc-", "x-campaign-", "x-sendgrid-", "x-ses-")) or "x-feedback-id" in names:
        add("campaign_header", "campaign or bulk-mail header")
    body = normalize(email.plain_text + "\n" + email.html_text)
    if any(phrase in body for phrase in ("unsubscribe", "manage preferences", "email preferences", "配信停止", "購読解除")):
        add("unsubscribe_text", "unsubscribe expression in body")
    if any(phrase in body for phrase in ("view in browser", "view this email in your browser", "ブラウザで表示")):
        add("view_in_browser", "view-in-browser expression in body")
    metrics = link_metrics(email)
    if metrics["utm_links"]:
        add("tracking_parameters", "email tracking parameter")
    if metrics["total_links"] >= many_links_threshold:
        add("many_links", f"HTML links: {email.html_link_count}")
    sender = normalize(email.sender)
    if any(value in sender for value in ("noreply", "no-reply", "notification")):
        add("automated_sender", "automated sender expression")
    return features, reasons


def keyword_locations(email: ParsedEmail, keywords: list[str], matching: dict) -> dict[str, list[str]]:
    fields = {"subject": email.subject, "sender": email.sender, "body": email.plain_text + "\n" + email.html_text,
              "url": "\n".join(email.html_links)}
    result: dict[str, list[str]] = {}
    for name, value in fields.items():
        hits = find_keywords(value, keywords, matching["min_alphanumeric_length"], matching["allow_short_exact_tokens"])
        if hits: result[name] = hits
    return result
