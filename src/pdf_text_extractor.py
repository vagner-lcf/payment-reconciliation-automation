from pypdf import PdfReader


def extract_text_from_pdf(file_path: str) -> str:
    """Extract embedded text from all pages of a PDF receipt.

    Join page contents with newline separators. Pages without
    extractable text contribute an empty string.

    Args:
        file_path: Path to the PDF receipt.

    Returns:
        The extracted text.
    """

    reader = PdfReader(file_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)