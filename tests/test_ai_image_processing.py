"""Unit tests for ai.image_processing (detect_text_from_image)."""
import io
from pathlib import Path

import pytest
from PIL import Image

from ai.image_processing import detect_text_from_image, OCRProcessor


def test_detect_text_from_image_file_not_found_raises():
    with pytest.raises(FileNotFoundError) as exc_info:
        detect_text_from_image("/nonexistent/path/image.jpg")
    assert "not found" in str(exc_info.value).lower() or "Image file" in str(exc_info.value)


def test_detect_text_from_image_valid_file_returns_string(tmp_path):
    path = tmp_path / "test.png"
    img = Image.new("RGB", (100, 100), color="white")
    img.save(path, format="PNG")
    result = detect_text_from_image(str(path))
    assert isinstance(result, str)
    # May be empty if tesseract finds no text
    assert result is not None


def test_ocr_processor_preprocess_image_returns_ndarray(tmp_path):
    path = tmp_path / "test.png"
    img = Image.new("RGB", (50, 50), color="white")
    img.save(path, format="PNG")
    processor = OCRProcessor()
    result = processor.preprocess_image(str(path))
    assert result is not None
    try:
        import numpy as np
        assert isinstance(result, np.ndarray)
    except ImportError:
        pass


def test_ocr_processor_extract_text_with_confidence_returns_tuple(tmp_path):
    import numpy as np
    path = tmp_path / "test.png"
    img = Image.new("RGB", (50, 50), color="white")
    img.save(path, format="PNG")
    processor = OCRProcessor()
    processed = processor.preprocess_image(str(path))
    text, confidence = processor.extract_text_with_confidence(processed)
    assert isinstance(text, str)
    assert isinstance(confidence, (int, float))
