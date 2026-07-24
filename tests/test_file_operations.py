from pathlib import Path

import pytest

from eml_newsletter_filter.file_operations import copy_unique, validate_input_output_paths


def test_output_inside_input_is_excluded_and_name_collision_is_preserved(tmp_path: Path):
    source = tmp_path / "input"
    output = source / "output"
    source.mkdir()
    mail = source / "mail.eml"
    mail.write_text("mail", encoding="utf-8")
    assert validate_input_output_paths(source, output) == output.resolve()
    target = copy_unique(mail, output / "newsletter")
    assert copy_unique(mail, output / "newsletter").name == "mail_1.eml"
    assert target.name == "mail.eml"


def test_same_or_nested_input_output_is_rejected(tmp_path: Path):
    same = tmp_path / "same"; same.mkdir()
    with pytest.raises(ValueError, match="same"):
        validate_input_output_paths(same, same)
    output = tmp_path / "output"; nested_input = output / "input"; nested_input.mkdir(parents=True)
    with pytest.raises(ValueError, match="inside the output"):
        validate_input_output_paths(nested_input, output)


def test_symlinked_same_path_is_rejected_when_supported(tmp_path: Path):
    source = tmp_path / "source"; source.mkdir()
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(source, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")
    with pytest.raises(ValueError, match="same"):
        validate_input_output_paths(source, alias)
