"""Base view for all section views."""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFrame, QHBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class BaseSectionView(QWidget):
    """Base class for section views."""

    def __init__(self, title: str, parent=None):
        """Initialize base section view."""
        super().__init__(parent)
        self.title = title
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the base UI structure."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Header with title and back button
        header = QFrame()
        header.setStyleSheet("background-color: #f8f9fa; border-radius: 5px;")
        header_layout = QHBoxLayout(header)
        
        # Back button
        back_btn = QPushButton("← Voltar")
        back_btn.clicked.connect(self.close)
        header_layout.addWidget(back_btn)
        
        # Title
        title_label = QLabel(self.title)
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label, 1)  # 1 is stretch factor
        
        # Add header to main layout
        layout.addWidget(header)
        
        # Content area (to be filled by subclasses)
        self.content_area = QFrame()
        self.content_area.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 20px;
            }
        """)
        layout.addWidget(self.content_area)
    
    def setup_content(self):
        """Setup the content area. Should be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement setup_content")