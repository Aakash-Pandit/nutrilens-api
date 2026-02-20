import logging

import cv2
import numpy as np
import pytesseract
from PIL import Image

import tempfile
from pathlib import Path


logger = logging.getLogger(__name__)


class OCRProcessor:
    def __init__(self, tesseract_path=None):
        # Only needed for Windows users
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

    def preprocess_image(self, image_path):
        """
        A robust pipeline to handle non-white backgrounds and noise.
        """
        # 1. Load image
        img = cv2.imread(image_path)
        
        # 2. Resize (OCR works best when text is at least 30px high)
        img = cv2.resize(img, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)

        # 3. Convert to Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 4. Denoise (Removes speckles from colored backgrounds)
        denoised = cv2.fastNlMeansDenoising(gray, h=10)

        # 5. Thresholding (Isolating text from background)
        # We use Adaptive Thresholding for messy/colored backgrounds
        thresh = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )

        # 6. Morphological Operations (Boldens the text)
        kernel = np.ones((1, 1), np.uint8)
        processed_img = cv2.dilate(thresh, kernel, iterations=1)
        processed_img = cv2.erode(processed_img, kernel, iterations=1)

        return processed_img

    def extract_text_with_confidence(self, processed_img):
        """
        Returns text and a confidence score to help decide if AI fallback is needed.
        """
        # Convert back to PIL for Tesseract if preferred, though CV2 works
        data = pytesseract.image_to_data(processed_img, output_type=pytesseract.Output.DICT)
        
        # Filter out empty results and calculate average confidence
        confidences = [int(c) for c in data['conf'] if int(c) != -1]
        text = " ".join([w for w in data['text'] if w.strip() != ""])
        
        avg_conf = sum(confidences) / len(confidences) if confidences else 0
        return text, avg_conf


def using_ocr_processor(file_path: str) -> tuple[str, int]:
    ocr = OCRProcessor()
    
    # Preprocess the "messy" image
    cleaned_img = ocr.preprocess_image(file_path)
    
    # Save for debugging (good for Docker volume checks)
    cv2.imwrite(f'debug_preprocessed_{file_path}.jpg', cleaned_img)
    
    # Extract
    result_text, confidence = ocr.extract_text_with_confidence(cleaned_img)
    
    logger.info(f"Confidence Score: {confidence}%")
    logger.info(f"Extracted Text:\n{result_text}")

    if confidence < 60:
        logger.warning("--- WARNING: Low confidence. Recommend triggering Gemini API fallback ---")
        return "", confidence

    return result_text, confidence


def detect_text_from_image(file_path: str) -> str:
    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Image file not found: {file_path}")

    # Load with PIL, convert to RGB, save as PNG so Tesseract gets a supported format
    image = Image.open(path)
    if image.mode != "RGB":
        image = image.convert("RGB")

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        temp_path = f.name
    try:
        image.save(temp_path, format="PNG")
        return pytesseract.image_to_string(temp_path).strip()
    finally:
        Path(temp_path).unlink(missing_ok=True)
