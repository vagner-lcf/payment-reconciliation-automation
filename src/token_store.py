import json
import os
from pathlib import Path


TOKEN_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "tiny_tokens.json"
)


def save_tokens(token_data: dict) -> None:
    """Save OAuth tokens to local storage."""
    TOKEN_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_file = TOKEN_FILE.with_suffix(".tmp")

    try:
        with temp_file.open("w", encoding="utf-8") as file:
            json.dump(token_data, file)

        os.replace(temp_file, TOKEN_FILE)

    finally:
        temp_file.unlink(missing_ok=True)


def load_tokens() -> dict | None:
    """Load stored OAuth tokens, returning None if unavailable or invalid."""

    if not TOKEN_FILE.exists():
        return None

    try:
        with TOKEN_FILE.open("r", encoding="utf-8") as file:
            token_data = json.load(file)

    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(token_data, dict):
        return None

    return token_data
