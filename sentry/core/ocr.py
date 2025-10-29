"""OCR processing utilities."""

import cv2
import numpy as np
try:
    import pytesseract
    _HAS_PYTESSERACT = True
except Exception:
    pytesseract = None
    _HAS_PYTESSERACT = False
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def preprocess_image(image):
    """Preprocess image for OCR."""
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply bilateral filter to remove noise while keeping edges
    denoised = cv2.bilateralFilter(gray, 11, 17, 17)
    
    # Adaptive thresholding
    thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    # Morphological operations to remove small noise
    kernel = np.ones((3,3), np.uint8)
    morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    
    return morph

def find_plate_region(image):
    """Find potential license plate regions in image."""
    edges = cv2.Canny(image, 30, 200)
    contours, _ = cv2.findContours(
        edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )
    
    # Sort contours by area
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
    
    for contour in contours:
        # Approximate the contour
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        
        # Look for rectangle-like contours
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(approx)
            
            # Check aspect ratio typical for Brazilian plates
            aspect = float(w) / h
            if 2.0 <= aspect <= 4.5:
                return (x, y, w, h)
    
    return None

def extract_plate_text(image, region=None):
    """Extract text from license plate image."""
    try:
        if region:
            x, y, w, h = region
            roi = image[y:y+h, x:x+w]
        else:
            roi = image
            
        # Preprocess
        processed = preprocess_image(roi)
        
        # OCR configuration for license plates
        config = '--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        
        # If pytesseract is not available, skip OCR gracefully
        if not _HAS_PYTESSERACT:
            logger.warning("pytesseract not available — OCR disabled")
            return None

        # Extract text
        text = pytesseract.image_to_string(
            processed, 
            config=config
        ).strip()
        
        # Validate format
        if len(text) >= 7:  # Brazilian plates are 7-8 chars
            return text
            
    except Exception as e:
        logger.error(f"OCR error: {e}")
    
    return None

def process_plate_image(image_path):
    """Process an image file to extract license plate text."""
    try:
        # Read image
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError("Failed to read image")
            
        # Find plate region
        region = find_plate_region(image)
        
        # Extract text
        text = extract_plate_text(image, region)
        
        if text:
            logger.info(f"Found plate text: {text}")
            return text
        else:
            logger.warning("No valid plate text found")
            return None
            
    except Exception as e:
        logger.error(f"Plate processing error: {e}")
        return None


def process_image(frame):
    """Process an image/frame (numpy array) and return detected plate text or None.

    This is a convenience wrapper used by the UI camera integration.
    """
    try:
        if frame is None:
            return None

        # Find plate region in the frame
        region = find_plate_region(frame)
        text = extract_plate_text(frame, region)
        return text
    except Exception as e:
        logger.error(f"process_image error: {e}")
        return None