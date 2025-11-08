"""Main application entry point."""

import sys
import logging
from logging.handlers import RotatingFileHandler
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

from . import config
from .ui.views.login_view import LoginView
from .ui.views.dashboard_view import DashboardView
from .data.database import init_db

def setup_logging():
    """Configure application logging with rotation and colored console if available."""
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.LOG_LEVEL))

    # Rotating file handler
    file_handler = RotatingFileHandler(
        filename=str(config.LOG_FILE),
        maxBytes=2 * 1024 * 1024,  # 2MB
        backupCount=5,
        encoding='utf-8'
    )
    file_fmt = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    # Console handler (colored if colorlog available)
    try:
        import colorlog  # type: ignore
        console_handler = colorlog.StreamHandler()
        console_handler.setFormatter(colorlog.ColoredFormatter(
            '%(log_color)s%(levelname)-8s%(reset)s | %(blue)s%(name)s%(reset)s | %(message)s',
            log_colors={
                'DEBUG': 'cyan', 'INFO': 'green', 'WARNING': 'yellow', 'ERROR': 'red', 'CRITICAL': 'bold_red'
            }
        ))
    except Exception:
        console_handler = logging.StreamHandler()
        console_fmt = logging.Formatter('%(levelname)-8s | %(name)s | %(message)s')
        console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

def main():
    """Initialize and run the SENTRY application."""
    try:
        # Setup logging first
        setup_logging()
        logging.info("Starting SENTRY application...")

        # Initialize database
        init_db()
        logging.info("Database initialized")
        
        # Create Qt application
        app = QApplication(sys.argv)
        
        # Set default font
        app.setFont(QFont("Arial", 10))
        
        # Create and show main window
        from .ui.main_window import MainWindow
        window = MainWindow()
        window.setWindowTitle(config.APP_NAME)
        window.showMaximized()
        
        logging.info("Application UI initialized")
        return app.exec_()

    except Exception as e:
        logging.error(f"Application startup error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
