from email import policy
from email.header import decode_header
from email.parser import BytesParser
from email.utils import getaddresses, parseaddr
from pathlib import Path

from .html_text import html_to_text_and_link_count
from .models import ParsedEmail


def _decode_header(value: str | None) -> str:
    if not value:
        return ""
    parts: list[str] = []
    for fragment, charset in decode_header(value):
        if isinstance(fragment, bytes):
            for encoding in (charset, "utf-8", "iso-2022-jp", "cp932", "latin-1"):
                if not encoding:
                    continue
                try:
                    parts.append(fragment.decode(encoding, errors="replace"))
                    break
                except (LookupError, UnicodeDecodeError):
                    continue
        else:
            parts.append(fragment)
    return "".join(parts)


def _part_text(part) -> str:
    try:
        content = part.get_content()
        return content if isinstance(content, str) else content.decode("utf-8", errors="replace")
    except Exception:
        data = part.get_payload(decode=True) or b""
        charset = part.get_content_charset() or "utf-8"
        try:
            return data.decode(charset, errors="replace")
        except LookupError:
            return data.decode("utf-8", errors="replace")


def parse_eml(path: Path) -> ParsedEmail:
    raw = path.read_bytes()
    if not raw.strip():
        raise ValueError("Empty EML file")
    message = BytesParser(policy=policy.default).parsebytes(raw)
    if not list(message.keys()):
        raise ValueError("No message headers found")
    headers: dict[str, list[str]] = {}
    for key in message.keys():
        headers.setdefault(key.lower(), []).append(_decode_header(str(message[key])))
    from_value = _decode_header(str(message.get("From", "")))
    sender_name, sender_address = parseaddr(from_value)
    plain_parts: list[str] = []
    html_parts: list[str] = []
    for part in message.walk():
        if part.is_multipart() or part.get_content_disposition() == "attachment" or part.get_filename():
            continue
        content_type = part.get_content_type().lower()
        if content_type == "text/plain":
            plain_parts.append(_part_text(part))
        elif content_type == "text/html":
            html_parts.append(_part_text(part))
    html_raw = "\n".join(html_parts)
    html_text, links, hrefs = html_to_text_and_link_count(html_raw)
    recipients = [address for _, address in getaddresses(
        [str(value) for name in ("To", "Cc") for value in message.get_all(name, [])]
    )]
    return ParsedEmail(path, _decode_header(str(message.get("Subject", ""))), sender_name,
                       sender_address, recipients, headers, "\n".join(plain_parts), html_text, html_raw, links, hrefs)
