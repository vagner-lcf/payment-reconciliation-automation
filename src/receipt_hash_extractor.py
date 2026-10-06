import hashlib


def extract_receipt_hash(file_path: str) -> str:
    with open(file_path, "rb") as file:
        file_bytes = file.read()
       
    return hashlib.sha256(file_bytes).hexdigest()