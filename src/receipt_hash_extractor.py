import hashlib


def extract_receipt_hash(file_path: str) -> str:
    """Calculate the SHA-256 hash of a receipt file.

    Hash the original file bytes to support duplicate-file detection.

    Args:
        file_path: Path to the receipt.

    Returns:
        The hexadecimal SHA-256 digest.
    """

    with open(file_path, "rb") as file:
        file_bytes = file.read()
       
    return hashlib.sha256(file_bytes).hexdigest()