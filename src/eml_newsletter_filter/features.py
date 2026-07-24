import re
import unicodedata

from .models import ParsedEmail


def normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def find_keywords(text: str, keywords: list[str]) -> list[str]:
    normalized = normalize(text)
    return [keyword for keyword in keywords if normalize(str(keyword)) in normalized]


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
    tracking_source = normalize(email.plain_text + "\n" + email.html_raw)
    if any(value in tracking_source for value in ("utm_source", "utm_medium=email", "utm_campaign")):
        add("tracking_parameters", "email tracking parameter")
    if email.html_link_count >= many_links_threshold:
        add("many_links", f"HTML links: {email.html_link_count}")
    sender = normalize(email.sender)
    if any(value in sender for value in ("noreply", "no-reply", "notification")):
        add("automated_sender", "automated sender expression")
    return features, reasons
