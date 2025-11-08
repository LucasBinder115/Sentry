"""Base view class with common functionality for all views."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QGraphicsDropShadowEffect,
    QLabel, QHBoxLayout, QPushButton
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

from ..styles.theme import Colors, StyleSheet, Fonts, Icons

class BaseView(QWidget):
    """Base class for all views with common styling and functionality."""
    
    def __init__(self, title: str, parent=None):
        """Initialize base view."""
        super().__init__(parent)
        self.title = title
        self.setup_base_ui()
    
    def setup_base_ui(self):
        """Setup the base UI elements."""
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)
        
        # Header section
        self.setup_header()
        
        # Content area
        self.content_frame = QFrame()
        self.content_frame.setStyleSheet(StyleSheet.FRAME)
        
        # Add shadow to content frame
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 2)
        self.content_frame.setGraphicsEffect(shadow)
        
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(20)
        
        self.main_layout.addWidget(self.content_frame)
    
    def setup_header(self):
        """Setup the header section."""
        header = QFrame()
        header.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(5)
        
        title_label = QLabel(self.title)
        title_label.setStyleSheet(Fonts.title())
        title_layout.addWidget(title_label)
        
        description = self.get_description()
        if description:
            desc_label = QLabel(description)
            desc_label.setStyleSheet(Fonts.small())
            title_layout.addWidget(desc_label)
        
        header_layout.addWidget(title_container)
        
        # Action buttons
        self.action_buttons = QFrame()
        self.action_buttons.setStyleSheet("background: transparent;")
        self.action_layout = QHBoxLayout(self.action_buttons)
        self.action_layout.setContentsMargins(0, 0, 0, 0)
        self.action_layout.setSpacing(10)
        
        # Add default actions
        self.setup_action_buttons()
        
        header_layout.addWidget(self.action_buttons)
        self.main_layout.addWidget(header)
    
    def setup_action_buttons(self):
        """Setup action buttons in header. Override in subclasses."""
        pass
    
    def get_description(self) -> str:
        """Get view description. Override in subclasses."""
        return ""
    
    def add_action_button(self, text: str, icon: str, style: str,
                         callback, tooltip: str = None) -> QPushButton:
        """Add an action button to the header."""
        btn = QPushButton(f"{icon} {text}")
        btn.setStyleSheet(style)
        btn.setCursor(Qt.PointingHandCursor)
        if tooltip:
            btn.setToolTip(tooltip)
        btn.clicked.connect(callback)
        self.action_layout.addWidget(btn)
        return btn
    
    def show_loading(self, message: str = "Carregando..."):
        """Show loading indicator."""
        if not hasattr(self, 'loading_overlay'):
            from ..widgets.loading_overlay import LoadingOverlay
            self.loading_overlay = LoadingOverlay(self)
        
        self.loading_overlay.set_message(message)
        self.loading_overlay.show()
        self.loading_overlay.raise_()  # Bring to front
    
    def hide_loading(self):
        """Hide loading indicator."""
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.hide()
    
    def refresh(self):
        """Refresh view content. Override in subclasses."""
        pass