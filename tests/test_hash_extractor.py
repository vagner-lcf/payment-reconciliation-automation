from src.receipt_hash_extractor import extract_receipt_hash


def test_extract_receipt_hash_same_file_returns_same_hash():
    file_path = "tests/fixtures/receipts/mercado_pago_pix_openpdf.pdf"

    first_hash = extract_receipt_hash(file_path)
    second_hash = extract_receipt_hash(file_path)

    assert first_hash == second_hash

def test_extract_receipt_hash_different_files_return_different_hashes():
    first_file = "tests/fixtures/receipts/mercado_pago_pix_openpdf.pdf"
    second_file = "tests/fixtures/receipts/mercado_pago_pix_fpdf.pdf"

    first_hash = extract_receipt_hash(first_file)
    second_hash = extract_receipt_hash(second_file)

    assert first_hash != second_hash

def test_extract_receipt_hash_returns_sha256_hex_string():
    file_path = "tests/fixtures/receipts/mercado_pago_pix_openpdf.pdf"

    result = extract_receipt_hash(file_path)

    assert isinstance(result, str)
    assert len(result) == 64