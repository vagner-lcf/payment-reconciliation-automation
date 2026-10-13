from google.cloud import vision


def extract_text_from_image(file_path: str) -> str:
    """
    Extracts text from an image file using Google Cloud Vision API.

    Args:
        file_path (str): The path to the image file.

    Returns:
        str: The extracted text from the image.
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
