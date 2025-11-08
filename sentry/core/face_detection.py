"""Simple human face detection using OpenCV Haar Cascade."""

import cv2
import os
from typing import Optional

# Try to resolve the default haarcascade path that ships with OpenCV
_DEF_CASCADE_PATH = None
try:
    _DEF_CASCADE_PATH = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
except Exception:
    _DEF_CASCADE_PATH = None

_classifier: Optional[cv2.CascadeClassifier] = None


def _get_classifier() -> Optional[cv2.CascadeClassifier]:
    global _classifier
    if _classifier is not None:
        return _classifier
    try:
        cascade_path = _DEF_CASCADE_PATH
        if cascade_path and os.path.isfile(cascade_path):
            clf = cv2.CascadeClassifier(cascade_path)
            if not clf.empty():
                _classifier = clf
                return _classifier
    except Exception:
        pass
    return None


def detect_human_face(frame) -> bool:
    """Returns True if a human face is detected in the given BGR frame."""
    try:
        if frame is None:
            return False
        clf = _get_classifier()
        if clf is None:
            return False
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = clf.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        return len(faces) > 0
    except Exception:
        return False
