from google.cloud import vision


def extract_text_from_image(file_path: str) -> str:
    """Extract receipt text using Google Cloud Vision OCR.

    Send the image content to the document text detection API.

    Args:
        file_path: Path to the image receipt.

    Returns:
        The text recognized by Google Cloud Vision.

    Raises:
        RuntimeError: If the Vision API reports an error.
    """

    with open(file_path, "rb") as file:
        content = file.read()

    image = vision.Image(content=content)
    client = vision.ImageAnnotatorClient()
    response = client.document_text_detection(image=image)

    if response.error.message:
        raise RuntimeError(f"Google Cloud Vision error: {response.error.message}")

    text = response.full_text_annotation.text

    return text
