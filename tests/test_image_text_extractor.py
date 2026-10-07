import pytest
from unittest.mock import patch, MagicMock
from src.image_text_extractor import extract_text_from_image


def test_extract_text_from_image(tmp_path):
    image_path = tmp_path / "test_image.jpg"
    image_path.write_bytes(b"fake image content")
    
    with patch(
        "src.image_text_extractor.vision.ImageAnnotatorClient"
    ) as mock_client:
        mock_client_instance = mock_client.return_value

        mock_response = MagicMock()
        mock_response.error.message = ""
        mock_response.full_text_annotation.text = "texto extraído"

        mock_client_instance.document_text_detection.return_value = mock_response

        result = extract_text_from_image(str(image_path))

    assert result == "texto extraído"


def test_returns_empty_string_when_no_text_is_detected(tmp_path):
    image_path = tmp_path / "test_image.jpg"
    image_path.write_bytes(b"fake image content")
    
    with patch(
        "src.image_text_extractor.vision.ImageAnnotatorClient"
    ) as mock_client:
        mock_client_instance = mock_client.return_value

        mock_response = MagicMock()
        mock_response.error.message = ""
        mock_response.full_text_annotation.text = ""

        mock_client_instance.document_text_detection.return_value = mock_response

        result = extract_text_from_image(str(image_path))

    assert result == ""


def test_raises_runtime_error_when_vision_returns_error(tmp_path):
    image_path = tmp_path / "test_image.jpg"
    image_path.write_bytes(b"fake image content")

    with patch(
        "src.image_text_extractor.vision.ImageAnnotatorClient"
    ) as mock_client:
        mock_client_instance = mock_client.return_value

        mock_response = MagicMock()
        mock_response.error.message = "simulated Vision error"

        mock_client_instance.document_text_detection.return_value = mock_response

        with pytest.raises(RuntimeError, match="simulated Vision error"):
            extract_text_from_image(str(image_path))


def test_raises_file_not_found_error_when_image_does_not_exist():
    with pytest.raises(FileNotFoundError):
        extract_text_from_image("nonexistent_image.jpg")


