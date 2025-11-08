"""Application configuration module."""

import os
from pathlib import Path

# Base paths
ROOT_DIR = Path(__file__).parent.absolute()
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"
PHOTOS_DIR = DATA_DIR / "photos"
EXPORTS_DIR = DATA_DIR / "exports"
CONFIG_DIR = ROOT_DIR / "config"
PLUGINS_DIR = ROOT_DIR / "plugins"

# Database
DB_PATH = DATA_DIR / "database" / "database.db"

# Ensure required directories exist
for directory in [DATA_DIR, LOGS_DIR, PHOTOS_DIR, EXPORTS_DIR, DB_PATH.parent, CONFIG_DIR, PLUGINS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Logging
LOG_FILE = LOGS_DIR / "sentry.log"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# App settings
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
APP_NAME = "SENTRY - Sistema de Controle de Acesso"
