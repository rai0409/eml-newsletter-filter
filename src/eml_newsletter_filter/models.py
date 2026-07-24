from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedEmail:
    source_file: Path
    subject: str
    sender_name: str
    sender_address: str
    headers: dict[str, list[str]]
    plain_text: str
    html_text: str
    html_raw: str
    html_link_count: int

    @property
    def sender(self) -> str:
        return f"{self.sender_name} <{self.sender_address}>" if self.sender_name else self.sender_address

    @property
    def searchable_text(self) -> str:
        return "\n".join((self.subject, self.sender_name, self.sender_address, self.plain_text, self.html_text))


@dataclass
class ClassificationResult:
    source_file: str
    output_file: str | None
    classification: str
    score: int
    subject: str
    sender: str
    matched_features: list[str] = field(default_factory=list)
    matched_add_keywords: list[str] = field(default_factory=list)
    matched_exclude_keywords: list[str] = field(default_factory=list)
    matched_force_keywords: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    parse_error: str | None = None
