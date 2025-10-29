"""Main application entry point."""

import sys
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

from . import config
from .ui.views.login_view import LoginView
from .ui.views.dashboard_view import DashboardView
from .data.database import init_db

def setup_logging():
    """Configure application logging."""
    handlers = [
        logging.StreamHandler(),
        logging.FileHandler(str(config.LOG_FILE))
    ]
    
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

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
