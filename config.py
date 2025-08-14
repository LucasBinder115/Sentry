# sentry/config.py
import os
from pathlib import Path

class Config:
    # Database
    DB_PATH = Path(__file__).parent.parent / "data" / "registros.db"
    
    # Auth
    ADMIN_USER = os.getenv("ADMIN_USER", "admin")
    ADMIN_PASS = os.getenv("ADMIN_PASS", "admin123")
    
    # OCR
    TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Uso: from sentry.config import Config