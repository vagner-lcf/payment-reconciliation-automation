import json
import os
from pathlib import Path


TOKEN_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "tiny_tokens.json"
)


def save_tokens(token_data: dict) -> None:
    """Persist OAuth token data to a local JSON file.

    Write the data to a temporary file and replace the destination
    only after serialization completes.

    Args:
        token_data: OAuth token data to persist.

    Note:
        File replacement does not provide encryption or restrict
        access to the current Windows user.
    """

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
    """Load OAuth token data from the local JSON file.

    Returns:
        The stored token dictionary, or None if the file is missing,
        unreadable, contains invalid JSON, or has an unexpected type.
    """

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
