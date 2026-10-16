from decimal import Decimal
from datetime import date, datetime
import re


def extract_receipt_data(
    text: str,
    source_type: str = "pdf",
) -> dict:
    """Extract structured payment information from receipt text.

    Identify the provider and payment type, then extract payment details
    using the rules applicable to PDF or OCR-based image receipts.

    For supported boleto image layouts, the payment amount is accepted
    only when an OCR candidate matches the amount encoded in the barcode.

    Unknown image layouts and Pix transfers do not have their payment
    amount inferred automatically.

    Args:
        text: Text extracted from the payment receipt.
        source_type: Receipt source, either "pdf" or "image".

    Returns:
        A dictionary containing payment details, transaction identifiers,
        receipt layout, barcode data, and amount validation information.

    Raises:
        ValueError: If source_type is unsupported.
    """

    if source_type not in ("pdf", "image"):
        raise ValueError(
            f"Origem de comprovante não suportada: {source_type}"
        )

    provider = identify_provider(text)
    payment_type = identify_payment_type(text)

    receipt_layout = "unknown"
    barcode = None
    barcode_amount = None
    amount_matches_barcode = None

    if source_type == "pdf":
        # Keep the existing PDF amount extraction rules.
        amount = extract_amount(text, payment_type)

    else:
        receipt_layout = identify_receipt_layout(text)

        if receipt_layout in ("mp_pag_bol", "mp_pix_bol"):
            candidates = extract_ocr_amount_candidates(
                text, receipt_layout
            )

            barcode = extract_barcode(text)

            if barcode is not None:
                barcode_amount = extract_barcode_amount(barcode)

            if barcode_amount is not None and barcode_amount in candidates:
                amount = barcode_amount
                amount_matches_barcode = True

            elif barcode_amount is not None and candidates:
                amount = None
                amount_matches_barcode = False

            else:
                amount = None

        else:
            # Pix transfers and unknown layouts:
            # Do not infer an amount automatically.
            amount = None

    if source_type == "image":
        payment_date = extract_ocr_payment_date(text)
    else:
        payment_date = extract_payment_date(text, payment_type)

    if source_type == "image":
        beneficiary_document = extract_ocr_beneficiary_document(
            text,
            receipt_layout,
        )
    else:
        beneficiary_document = extract_beneficiary_document(
            text,
            payment_type,
        )

    pix_transaction_id = extract_pix_transaction_id(
        text, payment_type
    )

    if source_type == "image" and receipt_layout == "mp_pag_bol":
        provider_transaction_id = extract_ocr_mp_operation_id(text)
    else:
        provider_transaction_id = extract_boleto_transaction_id(
            text, payment_type
        )

    return {
        "provider": provider,
        "payment_type": payment_type,
        "amount": amount,
        "payment_date": payment_date,
        "beneficiary_document": beneficiary_document,
        "pix_transaction_id": pix_transaction_id,
        "provider_transaction_id": provider_transaction_id,
        "receipt_layout": receipt_layout,
        "barcode": barcode,
        "barcode_amount": barcode_amount,
        "amount_matches_barcode": amount_matches_barcode,
    }


def identify_provider(text: str) -> str:
    """Identify the payment provider from supported receipt text patterns."""

    text_clean = text.lower()

    # Check supported provider name variations.
    if any(provider in text_clean for provider in ["mercadopago", "mercado pago"]):
        return "mercado_pago"

    return "unknown"

def identify_payment_type(text: str) -> str:
    """Classify the receipt as Pix, boleto, or unknown."""

    text_clean = text.lower()

    # Check Pix first because its keywords are more specific.
    pix_keywords = ["comprovante de pix", "transação pix", "pagamento pix"]
    if any(keyword in text_clean for keyword in pix_keywords):
        return "pix"

    # Check boleto keywords.
    boleto_keywords = [
        "comprovante de pagamento de boleto",
        "pagamento de boleto",
        "código de barras",
        "linha digitável",
        "vencimento do boleto",
    ]
    if any(keyword in text_clean for keyword in boleto_keywords):
        return "boleto"

    return "unknown"


def identify_receipt_layout(text: str) -> str:
    """Identify a supported Mercado Pago receipt layout.

    Returns:
        "mp_pag_bol" for boleto payments,
        "mp_pix_bol" for Pix boleto payments,
        "mp_pix_tra" for Pix transfers, or
        "unknown" when no supported layout is identified.
    """

    text_clean = " ".join(text.lower().split())

    if (
        "mercado pago" in text_clean
        and "comprovante de pagamento" in text_clean
        and "código de barras" in text_clean
    ):
        return "mp_pag_bol"

    if (
        "mercado pago" in text_clean
        and "comprovante de pix" in text_clean
    ):
        if "codbarra" in text_clean or "valor original" in text_clean:
            return "mp_pix_bol"

        if "origem e destino" in text_clean:
            return "mp_pix_tra"

    return "unknown"


def extract_barcode(text: str) -> str | None:
    """Extract a numeric barcode with a supported length from OCR text."""

    match = re.search(
        r"(?:código de barras|codbarra)[ \t]*\n((?:[0-9. \t]+\n?)+)",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    barcode = re.sub(r"\D", "", match.group(1))

    if len(barcode) not in (44, 47, 48):
        return None

    return barcode

def extract_barcode_amount(barcode: str) -> Decimal | None:
    """Extract the encoded payment amount from a numeric barcode.

    Support the barcode lengths and value encoding formats currently
    handled by the receipt parser.

    Returns:
        The encoded amount as Decimal, or None when the barcode
        format is unsupported or does not contain a usable amount.
    """

    if not barcode.isdecimal():
        return None

    if barcode.startswith("8") and len(barcode) in (44, 48):
        if len(barcode) == 48:
            barcode = (
                barcode[0:11] +
                barcode[12:23] +
                barcode[24:35] +
                barcode[36:47]
            )

        if barcode[2] not in ("6", "8"):
            return None

        value_digits = barcode[4:15]
        return Decimal(value_digits) / 100

    elif len(barcode) == 44:
        return Decimal(barcode[9:19]) / 100

    elif len(barcode) == 47:
        return Decimal(barcode[37:47]) / 100

    return None


def extract_amount(
    text: str ,
    payment_type: str,
)-> Decimal | None:
    """Extract the paid amount from supported PDF receipt layouts.

    Returns:
        The payment amount as Decimal, or None if no supported
        amount pattern is found.
    """

    if payment_type == "boleto":
        match = re.search(r"Total pago\s*R\$\s*([\d.,]+)", text)

        if match:
            return Decimal(match.group(1).replace(".", "").replace(",", "."))

        return None

    if payment_type == "pix":
        match_fpdf = re.search(r"Total:\s*R\$\s*([\d.,]+)", text)
        match_openpdf = re.findall(r"R\$\s*([\d.,]+)", text)

        if match_fpdf:
            return Decimal(match_fpdf.group(1).replace(".", "").replace(",", "."))

        if len(match_openpdf) == 1:
            return Decimal(match_openpdf[0].replace(".", "").replace(",", "."))

    return None

def extract_ocr_amount_candidates(
    text: str,
    receipt_layout: str,
) -> set[Decimal]:
    """Extract possible payment amounts from supported OCR layouts.

    Returns:
        A set of Decimal candidates extracted from the receipt text,
        or an empty set when no supported amount is found.
    """

    if receipt_layout not in ("mp_pix_bol", "mp_pag_bol", "mp_pix_tra"):
        return set()

    match = re.search(
        r"Comprovante de (?:pagamento|Pix)[\s\S]*?R\$\s*([\d.,⁰¹²³⁴⁵⁶⁷⁸⁹]+)",
        text,
        re.IGNORECASE,
    )

    if not match:
        return set()

    return parse_ocr_amount_candidates(match.group(1))

def parse_ocr_amount_candidates(raw_amount: str) -> set[Decimal]:
    """Interpret OCR amount text, including superscript cent digits.

    When explicit superscript cents are present, construct one amount.
    Otherwise, return both whole-unit and cent-based interpretations.

    Returns:
        A set of possible Decimal amounts.
    """

    superscript_digits = "⁰¹²³⁴⁵⁶⁷⁸⁹"
    translation = str.maketrans(
    "⁰¹²³⁴⁵⁶⁷⁸⁹",
    "0123456789"
    )

    integer_part = ""
    cents_part = ""

    candidates = set()

    raw_amount = raw_amount.strip()
    if raw_amount == "":
        return candidates

    raw_amount = raw_amount.replace(".", "")
    for char in raw_amount:
        if char in superscript_digits:
            cents_part += char
        else:
            integer_part += char

    if cents_part:
        cents_normalized = cents_part.translate(translation)
        amount = Decimal(f"{integer_part}.{cents_normalized}")
        candidates.add(amount)

    else:
        whole_amount = Decimal(integer_part)
        cents_amount = Decimal(integer_part) / Decimal("100")

        candidates.add(whole_amount)
        candidates.add(cents_amount)

    return candidates


MONTHS_PT_BR = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}


def extract_ocr_payment_date(text: str) -> date | None:
    """Extract a payment date from supported Portuguese OCR date formats.

    Returns:
        The parsed payment date, or None if no valid date is found.
    """

    date_patterns = [
        # Example: 13 de outubro de 2026
        r"\b(\d{1,2})\s+de\s+([a-zçãéêíóôú]+)\s+de\s+(\d{4})\b",

        # Example: 29/setembro/2026
        r"\b(\d{1,2})/([a-zçãéêíóôú]+)/(\d{4})\b",
    ]

    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if not match:
            continue

        day = int(match.group(1))
        month_name = match.group(2).lower()
        year = int(match.group(3))

        month = MONTHS_PT_BR.get(month_name)

        if month is None:
            continue

        try:
            return date(year, month, day)
        except ValueError:
            return None

    return None

def extract_payment_date(text: str, payment_type: str) -> date | None:
    """Extract the payment date from supported PDF receipt formats."""

    if payment_type == "boleto":
        match_boleto = re.search(r"Data do pagamento\s*(\d{2}/\d{2}/\d{4})", text)

        return datetime.strptime(match_boleto.group(1), "%d/%m/%Y").date() if match_boleto else None

    if payment_type == "pix":
        match_pix_openpdf = re.search(
            r"Comprovante de Pix\s*(\d{1,2})/(\w+)/(\d{4})",
            text
        )

        match_pix_fpdf = re.search(
            r"Comprovante de Pagamento\s+[\w-]+,\s+(\d{1,2}) de (\w+) de (\d{4})",
            text
        )

        if match_pix_openpdf:
            day = int(match_pix_openpdf.group(1))
            month_name = match_pix_openpdf.group(2).lower()
            year = int(match_pix_openpdf.group(3))

            month = MONTHS_PT_BR.get(month_name)

            if month:
                return date(year, month, day)

        if match_pix_fpdf:
            day = int(match_pix_fpdf.group(1))
            month_name = match_pix_fpdf.group(2).lower()
            year = int(match_pix_fpdf.group(3))

            month = MONTHS_PT_BR.get(month_name)

            if month:
                return date(year, month, day)

        return None

    return None

def extract_ocr_beneficiary_document(
    text: str,
    receipt_layout: str,
) -> str | None:
    """Extract the beneficiary CPF/CNPJ from a supported OCR layout.

    For Pix layouts, use the destination document rather than the
    origin document. Reject masked or incomplete identifiers.

    Returns:
        The beneficiary document, or None if it cannot be extracted
        reliably.
    """

    if receipt_layout == "mp_pag_bol":
        match = re.search(
            r"CPF/CNPJ do beneficiário\s*[:\-]?\s*(\d{11}|\d{14})\b",
            text,
            re.IGNORECASE,
        )

        return match.group(1) if match else None

    if receipt_layout not in ("mp_pix_bol", "mp_pix_tra"):
        return None

    section_match = re.search(
        r"Origem e destino(.*?)"
        r"N[.°º\s]*transação do Mercado Pago",
        text,
        re.IGNORECASE | re.DOTALL,
    )

    if not section_match:
        return None

    section = section_match.group(1)

    document_matches = re.findall(
        r"\b(CPF|CNPJ):\s*([0-9.*\-\s/]+)",
        section,
        re.IGNORECASE,
    )

    if len(document_matches) < 2:
        return None

    document_type, raw_document = document_matches[-1]
    document = re.sub(r"\D", "", raw_document)

    expected_length = 11 if document_type.upper() == "CPF" else 14

    if "*" in raw_document or len(document) != expected_length:
        return None

    return document

def extract_beneficiary_document(text: str, payment_type: str) -> str | None:
    """Extract the beneficiary CPF/CNPJ from supported PDF receipts."""

    if payment_type == "boleto":
        match = re.search(r"Beneficiário.*?CPF/CNPJ\s*([\d./-]+)", text, re.DOTALL)

        return match.group(1) if match else None

    if payment_type == "pix":
        match = re.search(r"Para.*?CNPJ:\s*([\d./-]+)", text, re.DOTALL)

        return match.group(1) if match else None

    return None

def extract_pix_transaction_id(text: str, payment_type: str) -> str | None:
    """Extract the Pix transaction identifier when available."""

    if payment_type == "pix":
        match = re.search(r"ID d[ae] transação Pix\s*([A-Za-z0-9]+)", text)

        return match.group(1) if match else None

    return None

def extract_boleto_transaction_id(text: str, payment_type: str) -> str | None:
    """Extract the boleto transaction identifier when available."""

    if payment_type == "boleto":
        match = re.search(r"Comprovante de transação\s*#([0-9]+)", text)

        return match.group(1) if match else None

    return None

def extract_ocr_mp_operation_id(text: str) -> str | None:
    """Extract the Mercado Pago operation identifier from OCR text."""

    match = re.search(
        r"N\.\s*°\s*de operação de Mercado Pago\s*\n\s*(\d{12})\b",
        text,
        re.IGNORECASE,
    )

    return match.group(1) if match else None
