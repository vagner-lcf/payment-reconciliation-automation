from src.receipt_parser import (
    extract_payment_date,
    identify_receipt_layout,
    identify_provider,
    identify_payment_type,
    extract_amount,
    MONTHS_PT_BR,
    extract_payment_date,
    extract_beneficiary_document,
    extract_pix_transaction_id,
    extract_boleto_transaction_id,
    extract_receipt_data,
    parse_ocr_amount_candidates,
    extract_ocr_payment_date,
    extract_ocr_beneficiary_document,
    extract_ocr_mp_operation_id,
    )
import src.receipt_parser as receipt_parser
from src.pdf_text_extractor import extract_text_from_pdf
from decimal import Decimal
from datetime import date
from pathlib import Path
import pytest

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


def test_extract_ocr_payment_date():
    text = (
        "Comprovante de pagamento\n"
        "R$ 62595\n"
        "13 de outubro de 2026, 14:32\n"
    )

    assert extract_ocr_payment_date(text) == date(2026, 10, 13)


def test_extract_ocr_payment_date_invalid():
    text = "31 de fevereiro de 2026, 14:32"

    assert extract_ocr_payment_date(text) is None

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
        'amount_matches_barcode': None,
        'barcode': None,
        'barcode_amount': None,
        'receipt_layout': 'unknown'
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
        'amount_matches_barcode': None,
        'barcode': None,
        'barcode_amount': None,
        'receipt_layout': 'unknown'
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
        'amount_matches_barcode': None,
        'barcode': None,
        'barcode_amount': None,
        'receipt_layout': 'unknown'
    }

def test_extract_receipt_data_mp_pag_bol_image():
    text = Path(
        "tests/fixtures/receipts/mp_pag_bol_real_ocr.txt"
    ).read_text(encoding="utf-8")

    result = extract_receipt_data(text, source_type="image")

    assert result["provider"] == "mercado_pago"
    assert result["payment_type"] == "boleto"
    assert result["receipt_layout"] == "mp_pag_bol"

    assert result["amount"] == Decimal("625.95")
    assert result["barcode_amount"] == Decimal("625.95")
    assert result["amount_matches_barcode"] is True

    assert result["payment_date"] == date(2026, 10, 5)
    assert result["beneficiary_document"] == "12345678000195"
    assert result["provider_transaction_id"] == "123456789012"
    assert result["pix_transaction_id"] is None

def test_extract_receipt_data_mp_pix_bol_image():
    text = Path(
        "tests/fixtures/receipts/mp_pix_bol_real_ocr.txt"
    ).read_text(encoding="utf-8")

    result = extract_receipt_data(text, source_type="image")

    assert result["provider"] == "mercado_pago"
    assert result["payment_type"] == "pix"
    assert result["receipt_layout"] == "mp_pix_bol"

    assert result["amount"] == Decimal("779.83")
    assert result["barcode_amount"] == Decimal("779.83")
    assert result["amount_matches_barcode"] is True

    assert result["payment_date"] == date(2026, 9, 29)
    assert result["beneficiary_document"] == "11222333000181"
    assert result["pix_transaction_id"] == (
        "E00000000202609291848TESTEPIX001"
    )
    assert result["provider_transaction_id"] is None

def test_extract_receipt_data_mp_pix_tra_image():
    text = Path(
        "tests/fixtures/receipts/mp_pix_tra_real_ocr.txt"
    ).read_text(encoding="utf-8")

    result = extract_receipt_data(text, source_type="image")

    assert result["provider"] == "mercado_pago"
    assert result["payment_type"] == "pix"
    assert result["receipt_layout"] == "mp_pix_tra"

    assert result["amount"] is None
    assert result["barcode"] is None
    assert result["barcode_amount"] is None
    assert result["amount_matches_barcode"] is None

    assert result["payment_date"] == date(2026, 9, 29)
    assert result["beneficiary_document"] == "44555666000181"
    assert result["pix_transaction_id"] == (
        "E00000000202609291844TESTEPIX002"
    )
    assert result["provider_transaction_id"] is None


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            "mercado\npago\nComprovante de pagamento\nCódigo de barras",
            "mp_pag_bol",
        ),
        (
            "mercado\npago\nComprovante de Pix\ncodbarra",
            "mp_pix_bol",
        ),
        (
            "mercado\npago\nComprovante de Pix\nValor original",
            "mp_pix_bol",
        ),
        (
            "mercado\npago\nComprovante de Pix\ncodbara\nValor original",
            "mp_pix_bol",
        ),
        (
            "mercado\npago\nComprovante de Pix\nOrigem e destino",
            "mp_pix_tra",
        ),
        (
            "mercado\npago\nComprovante de Pix",
            "unknown",
        ),
        (
            "nubank\nComprovante de Pix",
            "unknown",
        ),
        (
            "texto sem identificação de comprovante",
            "unknown",
        ),
    ],
)
def test_identify_receipt_layout(text, expected):
    assert identify_receipt_layout(text) == expected

@pytest.mark.parametrize(
    "raw_amount, expected",
    [
        ("150⁰⁰", {Decimal("150.00")}),
        ("62595", {Decimal("62595"), Decimal("625.95")}),
        ("1.02068", {Decimal("102068"), Decimal("1020.68")}),
        ("348", {Decimal("348"), Decimal("3.48")}),
        ("", set()),
        ("   ", set()),
    ],
)
def test_parse_ocr_amount_candidates(raw_amount, expected):
    result = parse_ocr_amount_candidates(raw_amount)

    assert result == expected

@pytest.mark.parametrize(
    "candidates, barcode_amount, expected_amount, expected_match",
    [
        (
            {Decimal("625.95"), Decimal("62595")},
            Decimal("625.95"),
            Decimal("625.95"),
            True,
        ),
        (
            {Decimal("625.95"), Decimal("62595")},
            Decimal("700.00"),
            None,
            False,
        ),
        (
            {Decimal("625.95"), Decimal("62595")},
            None,
            None,
            None,
        ),
    ],
)
def test_extract_receipt_data_barcode_reconciliation(
    monkeypatch,
    candidates,
    barcode_amount,
    expected_amount,
    expected_match,
):
    monkeypatch.setattr(
        receipt_parser,
        "identify_receipt_layout",
        lambda text: "mp_pag_bol",
    )

    monkeypatch.setattr(
        receipt_parser,
        "extract_ocr_amount_candidates",
        lambda text, layout: candidates,
    )

    monkeypatch.setattr(
        receipt_parser,
        "extract_barcode",
        lambda text: "12345678901234567890123456789012345678901234",
    )

    monkeypatch.setattr(
        receipt_parser,
        "extract_barcode_amount",
        lambda barcode: barcode_amount,
    )

    result = receipt_parser.extract_receipt_data(
        "Texto fictício de comprovante",
        source_type="image",
    )

    assert result["amount"] == expected_amount
    assert result["amount_matches_barcode"] is expected_match
    assert result["barcode_amount"] == barcode_amount


def test_extract_receipt_data_mp_pag_bol_ocr_fixture():
    fixture_path = (
        Path(__file__).parent
        / "fixtures"
        / "receipts"
        / "mp_pag_bol_ocr.txt"
    )

    text = fixture_path.read_text(encoding="utf-8")

    result = extract_receipt_data(
        text,
        source_type="image",
    )

    assert result["provider"] == "mercado_pago"
    assert result["payment_type"] == "boleto"
    assert result["receipt_layout"] == "mp_pag_bol"

    assert result["barcode"] == (
        "00195000000000625951234567890123456789012345"
    )
    assert result["barcode_amount"] == Decimal("625.95")
    assert result["amount"] == Decimal("625.95")
    assert result["amount_matches_barcode"] is True

    assert result["payment_date"] == date(2026, 10, 13)


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            "Comprovante de Pix\n29/setembro/2026 às 15:49:02.",
            date(2026, 9, 29),
        ),
        (
            "Comprovante de Pix\n5/outubro/2026 às 10:38:50.",
            date(2026, 10, 5),
        ),
    ],
)
def test_extract_ocr_payment_date_pix_layouts(text, expected):
    assert extract_ocr_payment_date(text) == expected


@pytest.mark.parametrize(
    "text, receipt_layout, expected",
    [
        (
            "Beneficiário\n"
            "SOC LIT CAR SANTO AGOSTINHO\n"
            "CPF/CNPJ do beneficiário\n"
            "92736040000890\n"
            "Titular do boleto\n"
            "Tratoray Distribuidora\n"
            "CPF/CNPJ do titular do boleto\n"
            "50661361000157\n",
            "mp_pag_bol",
            "92736040000890",
        ),
        (
            "Beneficiário\n"
            "SINBRAX INDUSTRIA E COMERCIO DE PECAS\n"
            "PARA VEICULO\n"
            "CPF/CNPJ do beneficiário\n"
            "21035489000107\n"
            "Titular do boleto\n"
            "Tratoray Distribuidora\n"
            "CPF/CNPJ do titular do boleto\n"
            "50661361000157\n",
            "mp_pag_bol",
            "21035489000107",
        ),
        (
            "Origem e destino\n"
            "Mercado Pago\n"
            "CNPJ: 50.661.361/0001-57\n"
            "MINISTERIO DA FAZENDA\n"
            "Itaú Unibanco S.A.\n"
            "CNPJ: 00.394.460/0058-87\n",
            "mp_pix_bol",
            None,
        ),
        (
            "Origem e destino\n"
            "Mercado Pago\n"
            "CNPJ: 50.661.361/0001-57\n"
            "Karen dos Santos\n"
            "Nu Pagamentos S.A.\n"
            "CPF: ***.644.399-**\n",
            "mp_pix_tra",
            None,
        ),
    ],
)
def test_extract_ocr_beneficiary_document(
    text,
    receipt_layout,
    expected,
):
    assert extract_ocr_beneficiary_document(
        text,
        receipt_layout,
    ) == expected


@pytest.mark.parametrize(
    "receipt_layout, recipient_document, expected",
    [
        (
            "mp_pix_bol",
            "CNPJ: 00.394.460/0058-87",
            "00394460005887",
        ),
        (
            "mp_pix_tra",
            "CNPJ: 00.670.691/0001-30",
            "00670691000130",
        ),
        (
            "mp_pix_tra",
            "CPF: ***.644.399-**",
            None,
        ),
        (
            "mp_pix_tra",
            "CPF: ***.548.420-**",
            None,
        ),
        (
            "mp_pix_tra",
            "CPF: ***.826.809-**",
            None,
        ),
        (
            "mp_pix_tra",
            "CPF: ***.446.959-**",
            None,
        ),
    ],
)
def test_extract_ocr_beneficiary_document_pix(
    receipt_layout,
    recipient_document,
    expected,
):
    text = (
        "Origem e destino\n"
        "TRATORAY DISTRIBUIDORA\n"
        "Mercado Pago\n"
        "CNPJ: 50.661.361/0001-57\n"
        "Recipient Example\n"
        "Bank Example\n"
        f"{recipient_document}\n"
        "N.° transação do Mercado Pago\n"
    )

    assert extract_ocr_beneficiary_document(
        text,
        receipt_layout,
    ) == expected


@pytest.mark.parametrize(
    "operation_id",
    [
        "181605785991",
        "180481558813",
        "180481016053",
        "180328173445",
        "181329621554",
    ],
)
def test_extract_ocr_mp_operation_id(operation_id):
    text = (
        "Comprovante de pagamento\n"
        "N.° de operação de Mercado Pago\n"
        f"{operation_id}\n"
        "Beneficiário\n"
    )

    assert extract_ocr_mp_operation_id(text) == operation_id
