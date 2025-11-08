"""OCR processing utilities."""

import cv2
import numpy as np
import os
import re
from typing import Optional, List, Tuple
try:
    import pytesseract
    _HAS_PYTESSERACT = True
except Exception:
    pytesseract = None
    _HAS_PYTESSERACT = False

# Optional engines
try:
    import easyocr  # type: ignore
    _HAS_EASYOCR = True
except Exception:
    easyocr = None
    _HAS_EASYOCR = False

try:
    from paddleocr import PaddleOCR  # type: ignore
    _HAS_PADDLE = True
except Exception:
    PaddleOCR = None
    _HAS_PADDLE = False

from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Global settings for engine and preprocessing
_ENGINE = 'tesseract'  # 'tesseract' | 'easyocr' | 'paddle'
_ENHANCED_PREPROCESSING = True
_easy_reader = None
_paddle_reader = None
_CONF_THRESHOLD = 0.6
_WARNED_NO_PYTESS = False

# Auto-configure Tesseract path on Windows if available
if _HAS_PYTESSERACT:
    try:
        if os.name == 'nt':
            _default_tess = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
            if os.path.isfile(_default_tess):
                pytesseract.pytesseract.tesseract_cmd = _default_tess
                logger.info(f"Configured tesseract_cmd: {_default_tess}")
    except Exception:
        pass

def set_ocr_engine(name: str):
    """Select OCR engine: 'tesseract', 'easyocr', or 'paddle'."""
    global _ENGINE, _easy_reader, _paddle_reader
    name = (name or 'tesseract').lower()
    if name == 'easyocr':
        if not _HAS_EASYOCR:
            logger.warning("EasyOCR not available; falling back to tesseract")
            _ENGINE = 'tesseract'
        else:
            # Lazy-init easyocr Reader (Portuguese/English to help plates)
            if _easy_reader is None:
                try:
                    _easy_reader = easyocr.Reader(['en'], gpu=False)
                except Exception as e:
                    logger.error(f"EasyOCR init failed: {e}")
                    _ENGINE = 'tesseract'
                    return
            _ENGINE = 'easyocr'
    elif name == 'paddle':
        if not _HAS_PADDLE:
            logger.warning("PaddleOCR not available; falling back to tesseract")
            _ENGINE = 'tesseract'
        else:
            if _paddle_reader is None:
                try:
                    _paddle_reader = PaddleOCR(lang='en', use_angle_cls=True, show_log=False)
                except Exception as e:
                    logger.error(f"PaddleOCR init failed: {e}")
                    _ENGINE = 'tesseract'
                    return
            _ENGINE = 'paddle'
    else:
        _ENGINE = 'tesseract'
    logger.info(f"OCR engine set to: {_ENGINE}")

def set_preprocessing(enhanced: bool):
    """Enable or disable enhanced preprocessing pipeline."""
    global _ENHANCED_PREPROCESSING
    _ENHANCED_PREPROCESSING = bool(enhanced)

def set_confidence_threshold(thresh: float):
    """Set global confidence threshold used to decide OCR acceptance and fallbacks."""
    global _CONF_THRESHOLD
    try:
        t = float(thresh)
    except Exception:
        t = 0.6
    if t <= 0:
        t = 0.6
    _CONF_THRESHOLD = t

def set_tesseract_cmd(path: str):
    """Optionally set the pytesseract executable path explicitly."""
    try:
        if not path:
            return
        if not _HAS_PYTESSERACT:
            logger.warning("pytesseract not available; cannot set tesseract_cmd")
            return
        import os
        if os.path.isfile(path):
            pytesseract.pytesseract.tesseract_cmd = path
            logger.info(f"Configured tesseract_cmd: {path}")
        else:
            logger.warning(f"tesseract_cmd path not found: {path}")
    except Exception as e:
        logger.warning(f"Failed to set tesseract_cmd: {e}")

def _variance_of_laplacian(image: np.ndarray) -> float:
    """Compute Laplacian variance to estimate blur (higher = sharper)."""
    return float(cv2.Laplacian(image, cv2.CV_64F).var())

def _auto_contrast_brightness(gray: np.ndarray) -> np.ndarray:
    """Auto adjust brightness/contrast using histogram clipping."""
    # CLAHE for local contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    return clahe.apply(gray)

def _sharpen(image: np.ndarray) -> np.ndarray:
    """Unsharp masking to sharpen details."""
    blur = cv2.GaussianBlur(image, (0, 0), 1.0)
    return cv2.addWeighted(image, 1.5, blur, -0.5, 0)

def preprocess_image(image: np.ndarray) -> np.ndarray:
    """Preprocess image for OCR with optional enhanced pipeline."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if _ENHANCED_PREPROCESSING:
        gray = _auto_contrast_brightness(gray)
        gray = _sharpen(gray)
        denoised = cv2.bilateralFilter(gray, 7, 50, 50)
        thresh = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    else:
        denoised = cv2.bilateralFilter(gray, 11, 17, 17)
        thresh = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    kernel = np.ones((3,3), np.uint8)
    morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    return morph

def _order_points(pts: np.ndarray) -> np.ndarray:
    """Return points ordered as (tl, tr, br, bl)."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def _four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Perspective transform to warp a plate region to a flat view."""
    rect = _order_points(pts)
    (tl, tr, br, bl) = rect
    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    maxWidth = int(max(widthA, widthB))
    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)
    maxHeight = int(max(heightA, heightB))
    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]
    ], dtype="float32")
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
    return warped

def find_plate_region(image):
    """Find potential license plate region as bounding rect (x, y, w, h)."""
    edges = cv2.Canny(image, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    best_score = 0.0
    for c in contours:
        area = cv2.contourArea(c)
        if area < 500:  # skip tiny
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        x, y, w, h = cv2.boundingRect(approx)
        aspect = float(w) / float(h or 1)
        if 2.0 <= aspect <= 5.5 and w > 60 and h > 15:
            rect_area = float(w * h)
            fill_ratio = float(area) / rect_area if rect_area > 0 else 0.0
            score = fill_ratio * min(aspect / 3.0, 2.0)
            if score > best_score:
                best_score = score
                best = (x, y, w, h)
    return best

def detect_and_warp_plate(image: np.ndarray) -> Optional[np.ndarray]:
    """Detect a plate-like quadrilateral and return a deskewed ROI if found."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = _auto_contrast_brightness(gray)
    edged = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edged, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:20]
    best = None
    best_score = 0.0
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            pts = approx.reshape(4, 2).astype("float32")
            warped = _four_point_transform(image, pts)
            h, w = warped.shape[:2]
            if h == 0 or w == 0:
                continue
            aspect = float(w) / float(h)
            if 2.0 <= aspect <= 6.0:
                roi = warped
                roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                blur_val = _variance_of_laplacian(roi_gray)
                score = (min(aspect / 3.0, 2.0) * (blur_val / 100.0))
                if score > best_score:
                    best_score = score
                    best = roi
    return best

def extract_plate_text(image: np.ndarray, region=None):
    """Extract text and confidence from license plate image.
    Returns (text, confidence_float_0_1) or (None, 0.0).
    """
    try:
        if region:
            x, y, w, h = region
            roi = image[y:y+h, x:x+w]
        else:
            roi = image

        processed = preprocess_image(roi)

        def _normalize(text: str) -> str:
            t = ''.join(ch for ch in (text or '') if ch.isalnum()).upper()
            t = t.replace('O', '0') if sum(c.isdigit() for c in t) >= 3 else t
            return t

        def _score_plate_str(t: str) -> float:
            if not t:
                return 0.0
            # BR formats: ABC1234 or Mercosur ABC1D23
            patterns = [r'^[A-Z]{3}[0-9]{4}$', r'^[A-Z]{3}[0-9][A-Z][0-9]{2}$']
            for p in patterns:
                if re.match(p, t):
                    return 1.0
            return 0.5 if len(t) >= 5 else 0.0

        candidates: List[Tuple[str, float, str]] = []  # (text, conf, engine)

        engine = _ENGINE
        # Try selected engine first
        if engine == 'easyocr' and _HAS_EASYOCR and _easy_reader is not None:
            try:
                results = _easy_reader.readtext(processed)
                for ((_, _), text, conf) in results:
                    t = _normalize(text)
                    if len(t) >= 5:
                        candidates.append((t, float(conf), 'easyocr'))
            except Exception as e:
                logger.debug(f"EasyOCR run failed: {e}")
        elif engine == 'paddle' and _HAS_PADDLE and _paddle_reader is not None:
            try:
                out = _paddle_reader.ocr(processed, cls=True)
                for line in out:
                    for _, (text, conf) in line:
                        t = _normalize(text)
                        if len(t) >= 5:
                            candidates.append((t, float(conf), 'paddle'))
            except Exception as e:
                logger.debug(f"PaddleOCR run failed: {e}")
        else:
            if not _HAS_PYTESSERACT:
                # Warn only once for missing pytesseract
                global _WARNED_NO_PYTESS
                if not _WARNED_NO_PYTESS:
                    logger.warning("pytesseract not available — OCR disabled")
                    _WARNED_NO_PYTESS = True
                return None, 0.0
            config = '--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            try:
                data = pytesseract.image_to_data(processed, config=config, output_type=pytesseract.Output.DICT)
                for txt, conf in zip(data.get('text', []), data.get('conf', [])):
                    try:
                        c = float(conf)
                    except Exception:
                        c = -1.0
                    t = _normalize(txt)
                    if t and c >= 0:
                        candidates.append((t, c / 100.0, 'tesseract'))
            except Exception:
                text = pytesseract.image_to_string(processed, config=config).strip()
                t = _normalize(text)
                if len(t) >= 5:
                    candidates.append((t, 0.0, 'tesseract'))

        # If confidence is weak, try other engines as fallback
        need_fallback = (max((c for _, c, _ in candidates), default=0.0) < 0.6)
        if need_fallback:
            if engine != 'tesseract' and _HAS_PYTESSERACT:
                try:
                    config = '--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
                    data = pytesseract.image_to_data(processed, config=config, output_type=pytesseract.Output.DICT)
                    for txt, conf in zip(data.get('text', []), data.get('conf', [])):
                        try:
                            c = float(conf)
                        except Exception:
                            c = -1.0
                        t = _normalize(txt)
                        if t and c >= 0:
                            candidates.append((t, c / 100.0, 'tesseract'))
                except Exception:
                    pass
            if engine != 'easyocr' and _HAS_EASYOCR and _easy_reader is not None:
                try:
                    results = _easy_reader.readtext(processed)
                    for ((_, _), text, conf) in results:
                        t = _normalize(text)
                        if len(t) >= 5:
                            candidates.append((t, float(conf), 'easyocr'))
                except Exception:
                    pass
            if engine != 'paddle' and _HAS_PADDLE and _paddle_reader is not None:
                try:
                    out = _paddle_reader.ocr(processed, cls=True)
                    for line in out:
                        for _, (text, conf) in line:
                            t = _normalize(text)
                            if len(t) >= 5:
                                candidates.append((t, float(conf), 'paddle'))
                except Exception:
                    pass

        if candidates:
            # Select by regex score then confidence then length
            ranked = sorted(candidates, key=lambda x: (_score_plate_str(x[0]), x[1], len(x[0])), reverse=True)
            best_text, best_conf, used_engine = ranked[0]
            return best_text, float(best_conf)
    except Exception as e:
        logger.error(f"OCR error: {e}")
    return None, 0.0

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
        text, conf = extract_plate_text(image, region)
        
        if text:
            logger.info(f"Found plate text: {text} ({conf*100:.1f}%)")
            return text
        else:
            logger.warning("No valid plate text found")
            return None
            
    except Exception as e:
        logger.error(f"Plate processing error: {e}")
        return None


def process_image(frame):
    """Process an image/frame (numpy array) and return (text, confidence)."""
    try:
        if frame is None:
            return None, 0.0
        # Try deskewed detection first
        roi = detect_and_warp_plate(frame)
        if roi is not None:
            text, conf = extract_plate_text(roi, None)
            if text and conf >= _CONF_THRESHOLD:
                return text, conf
        # Fallback to rectangular region
        region = find_plate_region(frame)
        text, conf = extract_plate_text(frame, region)
        # If still weak, try toggling preprocessing
        if (not text) or conf < _CONF_THRESHOLD:
            prev = _ENHANCED_PREPROCESSING
            try:
                set_preprocessing(not prev)
                if roi is not None:
                    t2, c2 = extract_plate_text(roi, None)
                else:
                    t2, c2 = extract_plate_text(frame, region)
                if t2 and c2 > conf:
                    text, conf = t2, c2
            finally:
                set_preprocessing(prev)
        return text, conf
    except Exception as e:
        logger.error(f"process_image error: {e}")
        return None, 0.0

def detect_text_from_frame(frame) -> str:
    """Return raw OCR text from a frame without plate filtering (debugging aid)."""
    try:
        if frame is None:
            return ""
        if not _HAS_PYTESSERACT:
            return ""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray)
        raw = (text or "").strip()
        if raw:
            logger.debug(f"Raw OCR text: {raw[:200]}")
        return raw
    except Exception as e:
        logger.debug(f"detect_text_from_frame failed: {e}")
        return ""