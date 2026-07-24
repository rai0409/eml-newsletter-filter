from pathlib import Path
import shutil


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def validate_input_output_paths(input_path: Path, output_path: Path) -> Path | None:
    """Validate normalized paths and return an output subtree to exclude, if needed."""
    input_resolved = input_path.resolve()
    output_resolved = output_path.resolve()
    if input_resolved == output_resolved:
        raise ValueError("Input and output paths must not be the same")
    if _is_within(input_resolved, output_resolved):
        raise ValueError("Input path must not be inside the output path")
    if input_path.is_dir() and _is_within(output_resolved, input_resolved):
        return output_resolved
    return None


def eml_inputs(path: Path, excluded_root: Path | None = None) -> list[Path]:
    if not path.exists():
        raise FileNotFoundError(f"Input does not exist: {path}")
    if path.is_file():
        if path.suffix.lower() != ".eml":
            raise ValueError("A single input file must have a .eml extension")
        return [path]
    return sorted(
        item for item in path.rglob("*")
        if item.is_file() and item.suffix.lower() == ".eml"
        and (excluded_root is None or not _is_within(item.resolve(), excluded_root))
    )


def copy_unique(source: Path, destination_dir: Path) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    candidate = destination_dir / source.name
    index = 1
    while candidate.exists():
        candidate = destination_dir / f"{source.stem}_{index}{source.suffix}"
        index += 1
    shutil.copy2(source, candidate)
    return candidate
