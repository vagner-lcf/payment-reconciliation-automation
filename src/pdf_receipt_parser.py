from pypdf import PdfReader
from decimal import Decimal
from datetime import date, datetime
import re


def extract_text_from_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)

def identify_provider(text: str) -> str:
    text_clean = text.lower()
    
    # Verifica qualquer uma das variações em uma linha
    if any(provider in text_clean for provider in ["mercadopago", "mercado pago"]):
        return "mercado_pago"
        
    return "unknown"
        
def identify_payment_type(text: str) -> str:
    text_clean = text.lower()

    # 1. Checa por PIX primeiro (é mais específico)
    pix_keywords = ["comprovante de pix", "transação pix", "pagamento pix"]
    if any(keyword in text_clean for keyword in pix_keywords):
        return "pix"

    # 2. Checa por Boleto
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

def extract_amount(text: str , payment_type: str)-> Decimal | None:
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

def extract_payment_date(text: str, payment_type: str) -> date | None:   
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

def extract_beneficiary_document(text: str, payment_type: str) -> str | None:
    if payment_type == "boleto":
        match = re.search(r"Beneficiário.*?CPF/CNPJ\s*([\d./-]+)", text, re.DOTALL)

        return match.group(1) if match else None

    if payment_type == "pix":
        match = re.search(r"Para.*?CNPJ:\s*([\d./-]+)", text, re.DOTALL)

        return match.group(1) if match else None

    return None

def extract_pix_transaction_id(text: str, payment_type: str) -> str | None:
    if payment_type == "pix":
        match = re.search(r"ID d[ae] transação Pix\s*([A-Za-z0-9]+)", text)

        return match.group(1) if match else None

    return None

def extract_boleto_transaction_id(text: str, payment_type: str) -> str | None:
    if payment_type == "boleto":
        match = re.search(r"Comprovante de transação\s*#([0-9]+)", text)

        return match.group(1) if match else None

    return None

def extract_receipt_data(text: str) -> dict:
    provider = identify_provider(text)
    payment_type = identify_payment_type(text)
    amount = extract_amount(text, payment_type)
    payment_date = extract_payment_date(text, payment_type)
    beneficiary_document = extract_beneficiary_document(text, payment_type)
    pix_transaction_id = extract_pix_transaction_id(text, payment_type)
    provider_transaction_id = extract_boleto_transaction_id(text, payment_type)

    receipt_data = {
        "provider": provider,
        "payment_type": payment_type,
        "amount": amount,
        "payment_date": payment_date,
        "beneficiary_document": beneficiary_document,
        "pix_transaction_id": pix_transaction_id,
        "provider_transaction_id": provider_transaction_id
    }

    return receipt_data


if __name__ == "__main__":
    file_path_test_1 ="data/input/teste - Comprovante_000chxn7k3.pdf"
    file_path_test_2 ="data/input/teste - comprovante-163200597100.pdf"
    file_path_test_3 ="data/input/teste - comprovante-164566512680.pdf"
    file_path_test_mascarado ="data/input/boleto - 2026_06_02_08_40_00_919_receipt.pdf"

    
    text = extract_text_from_pdf(str(file_path_test_mascarado))

    provider = identify_provider(text)
    print(f"Provider: {provider}")

    payment_type = identify_payment_type(text)
    print(f"Payment Type: {payment_type}")

    amount = extract_amount(text, payment_type)
    print(f"Amount: {amount}")

    payment_date = extract_payment_date(text, payment_type)
    print(f"Payment Date: {payment_date}")

    beneficiary_document = extract_beneficiary_document(text, payment_type)
    print(f"Beneficiary Document: {beneficiary_document}")

    pix_transaction_id = extract_pix_transaction_id(text, payment_type)
    print(f"Pix Transaction ID: {pix_transaction_id}")

    boleto_transaction_id = extract_boleto_transaction_id(text, payment_type)
    print(f"Provider Transaction ID: {boleto_transaction_id}")

    receipt_data = extract_receipt_data(text)
    print(f"Receipt Data: {receipt_data}")