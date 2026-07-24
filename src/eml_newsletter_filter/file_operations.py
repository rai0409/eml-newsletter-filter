from pathlib import Path
import shutil


def eml_inputs(path: Path) -> list[Path]:
    if not path.exists():
        raise FileNotFoundError(f"Input does not exist: {path}")
    if path.is_file():
        if path.suffix.lower() != ".eml":
            raise ValueError("A single input file must have a .eml extension")
        return [path]
    return sorted(item for item in path.rglob("*") if item.is_file() and item.suffix.lower() == ".eml")


def copy_unique(source: Path, destination_dir: Path) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    candidate = destination_dir / source.name
    index = 1
    while candidate.exists():
        candidate = destination_dir / f"{source.stem}_{index}{source.suffix}"
        index += 1
    shutil.copy2(source, candidate)
    return candidate
