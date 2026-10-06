from src.pdf_receipt_parser import (
    extract_payment_date,
    extract_text_from_pdf,
    identify_provider,
    identify_payment_type,
    extract_amount,
    MONTHS_PT_BR,
    extract_payment_date,
    extract_beneficiary_document,
    extract_pix_transaction_id,
    extract_boleto_transaction_id,
    extract_receipt_data
    )
from decimal import Decimal
from datetime import date

def test_identify_provider_mercado_pago():
    text = "Comprovante de pagamento - Mercado Pago"
    
    provider = identify_provider(text)
    
    assert provider == "mercado_pago"

def test_identify_provider_unknown():
    text = "Comprovante de pagamento - Banco Santander"
    
    provider = identify_provider(text)
    
    assert provider == "unknown"


def test_identify_payment_type_pix():
    text = "ID da transação Pix - E00000000202606121905TESTEPIX002"
    
    payment_type = identify_payment_type(text)
    
    assert payment_type == "pix"

def test_identify_payment_type_boleto():
    text = "Código de barras 74891126100001242604509936961011114650000120000"
    
    payment_type = identify_payment_type(text)
    
    assert payment_type == "boleto"

def test_identify_payment_type_unknown():
    text = "Comprovante de DOC/TED - Mercado Pago"
    
    payment_type = identify_payment_type(text)
    
    assert payment_type == "unknown"


def test_extract_amount_boleto():
    text = "Total pago\nR$ 1.234,56"
    payment_type = "boleto"

    amount = extract_amount(text, payment_type)

    assert amount == Decimal("1234.56")

def test_extract_amount_pix_fpdf():
    text = "Total: R$ 1.234,56"
    payment_type = "pix"

    amount = extract_amount(text, payment_type)

    assert amount == Decimal("1234.56")

def test_extract_amount_pix_openpdf():
    text = "R$ 1.234,56"
    payment_type = "pix"

    amount = extract_amount(text, payment_type)

    assert amount == Decimal("1234.56")

def test_extract_amount_pix_multiple_values():
    text = "R$ 1.234,56\nR$ 2.345,67"
    payment_type = "pix"

    amount = extract_amount(text, payment_type)

    assert amount is None

def test_extract_amount_unknown():
    text = "Total: R$ 1.234,56"
    payment_type = "unknown"

    amount = extract_amount(text, payment_type)

    assert amount is None


def test_extract_payment_date_boleto():
    text = "Data do pagamento\n15/08/2026"
    payment_type = "boleto"

    payment_date = extract_payment_date(text, payment_type)

    assert payment_date == date(2026, 8, 15)

def test_extract_payment_date_pix_openpdf():
    text = "Comprovante de Pix\n15/Agosto/2026"
    payment_type = "pix"

    payment_date = extract_payment_date(text, payment_type)

    assert payment_date == date(2026, 8, 15)

def test_extract_payment_date_pix_fpdf():
    text = "Comprovante de Pagamento\nSexta-feira, \n15 de Agosto de 2026"
    payment_type = "pix"

    payment_date = extract_payment_date(text, payment_type)

    assert payment_date == date(2026, 8, 15)

def test_extract_payment_date_pix_unknown_month():
    text = "Comprovante de Pix\n15/MesInvalido/2026"
    payment_type = "pix"

    payment_date = extract_payment_date(text, payment_type)

    assert payment_date is None

def test_extract_payment_date_unknown_payment_type():
    text = "Data do pagamento\n15/08/2026"
    payment_type = "unknown"

    payment_date = extract_payment_date(text, payment_type)

    assert payment_date is None


def test_extract_beneficiary_document_boleto_masked_returns_none():
    text = extract_text_from_pdf("tests/fixtures/receipts/mercado_pago_boleto.pdf")

    result = extract_beneficiary_document(text, "boleto")

    assert result is None

def test_extract_beneficiary_document_pix_openpdf():
    text = extract_text_from_pdf("tests/fixtures/receipts/mercado_pago_pix_openpdf.pdf")

    result = extract_beneficiary_document(text, "pix")

    assert result == "98.765.432/0001-10"

def test_extract_beneficiary_document_pix_fpdf():
    text = extract_text_from_pdf("tests/fixtures/receipts/mercado_pago_pix_fpdf.pdf")

    result = extract_beneficiary_document(text, "pix")

    assert result == "11.222.333/0001-44"

def test_extract_beneficiary_document_unknown_payment_type_returns_none():
    result = extract_beneficiary_document("qualquer texto", "unknown")

    assert result is None


def test_extract_pix_transaction_id_openpdf():
    text = extract_text_from_pdf(
        "tests/fixtures/receipts/mercado_pago_pix_openpdf.pdf"
    )

    result = extract_pix_transaction_id(text, "pix")

    assert result == "E00000000202606081826TESTEPIX001"

def test_extract_pix_transaction_id_fpdf():
    text = extract_text_from_pdf(
        "tests/fixtures/receipts/mercado_pago_pix_fpdf.pdf"
    )

    result = extract_pix_transaction_id(text, "pix")

    assert result == "E00000000202606121905TESTEPIX002"

def test_extract_pix_transaction_id_returns_none_when_id_is_missing():
    text = "Comprovante de Pagamento Pix sem identificador"

    result = extract_pix_transaction_id(text, "pix")

    assert result is None

def test_extract_boleto_transaction_id():
    text = extract_text_from_pdf(
        "tests/fixtures/receipts/mercado_pago_boleto.pdf"
    )

    result = extract_boleto_transaction_id(text, "boleto")

    assert result == "161332456089"

def test_extract_boleto_transaction_id_returns_none_when_id_is_missing():
    text = "Comprovante de transação sem número"

    result = extract_boleto_transaction_id(text, "boleto")

    assert result is None


def test_transaction_id_extractors_return_none_for_wrong_payment_type():
    pix_text = "ID de transação Pix\nE10573521202606081826T2RoZsnruja"
    boleto_text = "Comprovante de transação\n#161332456089"

    assert extract_pix_transaction_id(pix_text, "boleto") is None
    assert extract_boleto_transaction_id(boleto_text, "pix") is None

def test_extract_and_classify_pix_openpdf():
    path = "tests/fixtures/receipts/mercado_pago_pix_openpdf.pdf"

    extracted_text = extract_text_from_pdf(path)

    provider = identify_provider(extracted_text)

    payment_type = identify_payment_type(extracted_text)

    amount = extract_amount(extracted_text, payment_type)

    assert "Comprovante de Pix" in extracted_text
    assert provider == "mercado_pago"
    assert payment_type == "pix"
    assert amount == Decimal("115.00")

def test_extract_and_classify_pix_fpdf():
    path = "tests/fixtures/receipts/mercado_pago_pix_fpdf.pdf"

    extracted_text = extract_text_from_pdf(path)

    provider = identify_provider(extracted_text)

    payment_type = identify_payment_type(extracted_text)

    amount = extract_amount(extracted_text, payment_type)

    assert "Comprovante de Pagamento" in extracted_text
    assert provider == "mercado_pago"
    assert payment_type == "pix"
    assert amount == Decimal("180")

def test_extract_and_classify_boleto():
    path = "tests/fixtures/receipts/mercado_pago_boleto.pdf"

    extracted_text = extract_text_from_pdf(path)

    provider = identify_provider(extracted_text)

    payment_type = identify_payment_type(extracted_text)

    amount = extract_amount(extracted_text, payment_type)

    assert "Comprovante de transação" in extracted_text
    assert provider == "mercado_pago"
    assert payment_type == "boleto"
    assert amount == Decimal("1200.00")


def test_extract_receipt_data_pix_openpdf():
    text = extract_text_from_pdf(
        "tests/fixtures/receipts/mercado_pago_pix_openpdf.pdf"
    )

    result = extract_receipt_data(text)

    assert result == {
        "provider": "mercado_pago",
        "payment_type": "pix",
        "amount": Decimal("115"),
        "payment_date": date(2026, 6, 8),
        "beneficiary_document": "98.765.432/0001-10",
        "pix_transaction_id": "E00000000202606081826TESTEPIX001",
        "provider_transaction_id": None,
    }

def test_extract_receipt_data_pix_fpdf():
    text = extract_text_from_pdf(
        "tests/fixtures/receipts/mercado_pago_pix_fpdf.pdf"
    )

    result = extract_receipt_data(text)

    assert result == {
        "provider": "mercado_pago",
        "payment_type": "pix",
        "amount": Decimal("180"),
        "payment_date": date(2026, 6, 12),
        "beneficiary_document": "11.222.333/0001-44",
        "pix_transaction_id": "E00000000202606121905TESTEPIX002",
        "provider_transaction_id": None,
    }

def test_extract_receipt_data_boleto():
    text = extract_text_from_pdf(
        "tests/fixtures/receipts/mercado_pago_boleto.pdf"
    )

    result = extract_receipt_data(text)

    assert result == {
        "provider": "mercado_pago",
        "payment_type": "boleto",
        "amount": Decimal("1200.00"),
        "payment_date": date(2026, 6, 2),
        "beneficiary_document": None,
        "pix_transaction_id": None,
        "provider_transaction_id": "161332456089",
    }