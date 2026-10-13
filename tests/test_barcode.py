from decimal import Decimal
import pytest

from src.receipt_parser import extract_barcode_amount


@pytest.mark.parametrize(
    "barcode, expected",
    [
        # Boleto bancário — 44 dígitos
        ("00190000000000150000000000000000000000000000", Decimal("150.00")),

        # Linha digitável bancária — 47 dígitos
        ("0" * 37 + "0000015000", Decimal("150.00")),

        # Arrecadação — 44 dígitos
        ("8582" + "00000932182" + "0" * 29, Decimal("9321.82")),

        # Arrecadação — 48 dígitos (4 blocos de 11 dados + 1 verificador)
        (
            "85820000093" + "0"
            + "21820000000" + "0"
            + "00000000000" + "0"
            + "00000000000" + "0",
            Decimal("9321.82"),
        ),
    ],
)
def test_extract_barcode_amount_valid(barcode, expected):
    assert extract_barcode_amount(barcode) == expected


@pytest.mark.parametrize(
    "barcode",
    [
        "",
        "123",
        "123ABC" + "0" * 38,
        "0" * 45,
        "0" * 48,  # 48 dígitos sem prefixo de arrecadação
        "8572" + "0" * 40,  # indicador de referência, não valor
        "8592" + "0" * 40,  # indicador de referência, não valor
    ],
)
def test_extract_barcode_amount_invalid(barcode):
    assert extract_barcode_amount(barcode) is None