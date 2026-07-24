from pathlib import Path

from eml_newsletter_filter.parser import parse_eml


def test_japanese_multipart_is_decoded_and_html_text_is_extracted():
    email = parse_eml(Path(__file__).parent / "fixtures" / "japanese_multipart.eml")
    assert email.subject == "今週のニュース"
    assert email.sender_name == "日本語ニュース"
    assert "配信停止" in email.plain_text
    assert "今週のニュース" in email.html_text
    assert email.html_link_count == 1
