from pathlib import Path

import yaml


def load_glossary(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict) or not all(
        isinstance(key, str) and isinstance(value, str) and key and value
        for key, value in data.items()
    ):
        raise ValueError("Glossary must map nonempty source strings to target strings")
    return data
