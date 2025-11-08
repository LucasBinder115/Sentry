"""Loading overlay widget for showing loading states."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame,
    QGraphicsOpacityEffect
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor

from ..styles.theme import Colors, Fonts

class LoadingOverlay(QWidget):
    """Semi-transparent loading overlay with animated dots."""
    
    def __init__(self, parent=None, message="Carregando"):
        super().__init__(parent)
        
        # Setup overlay
        self.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(255, 255, 255, 0.8);
                border-radius: 10px;
            }}
            QLabel {{
                color: {Colors.TEXT};
                background: transparent;
            }}
        """)
        
        # Make semi-transparent
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0.95)
        self.setGraphicsEffect(opacity_effect)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        # Loading container
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 20px;
            }
        """)
        container_layout = QVBoxLayout(container)
        
        # Loading icon (can be replaced with a spinning wheel animation)
        self.loading_label = QLabel("⏳")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("font-size: 32px;")
        container_layout.addWidget(self.loading_label)
        
        # Message
        self.message_label = QLabel(message)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet(Fonts.body())
        container_layout.addWidget(self.message_label)
        
        # Dots for animation
        self.dots_label = QLabel("...")
        self.dots_label.setAlignment(Qt.AlignCenter)
        self.dots_label.setStyleSheet(Fonts.body())
        container_layout.addWidget(self.dots_label)
        
        layout.addWidget(container)
        
        # Animation timer
        self.dot_count = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate_dots)
        self.timer.start(500)  # Update every 500ms
        
        # Hide initially
        self.hide()
    
    def animate_dots(self):
        """Animate the loading dots."""
        self.dot_count = (self.dot_count + 1) % 4
        self.dots_label.setText("." * self.dot_count)
    
    def set_message(self, message: str):
        """Update the loading message."""
        self.message_label.setText(message)
    
    def showEvent(self, event):
        """Start animation when shown."""
        super().showEvent(event)
        if not self.timer.isActive():
            self.timer.start()
    
    def hideEvent(self, event):
        """Stop animation when hidden."""
        super().hideEvent(event)
        if self.timer.isActive():
            self.timer.stop()
    
    def paintEvent(self, event):
        """Custom paint for rounded corners."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw rounded rectangle background
        painter.setBrush(QColor(255, 255, 255, 204))  # Semi-transparent white
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 10, 10)
    
    def resizeEvent(self, event):
        """Ensure overlay covers parent widget."""
        if self.parentWidget():
            self.setGeometry(self.parentWidget().rect())