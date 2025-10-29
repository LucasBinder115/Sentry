"""Base form dialog for data entry."""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QHBoxLayout, QComboBox, QLabel,
    QFrame, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class BaseFormDialog(QDialog):
    """Base dialog for data entry forms."""
    
    def __init__(self, title: str, parent=None):
        """Initialize form dialog."""
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)  # Block interaction with parent window
        self.setMinimumWidth(400)
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Title
        title = QLabel(self.windowTitle())
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Form container
        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        self.form_layout = QFormLayout(form_frame)
        self.form_layout.setSpacing(10)
        layout.addWidget(form_frame)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        
        save_btn = QPushButton("Salvar")
        save_btn.clicked.connect(self.validate_and_save)
        save_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(save_btn)
        
        layout.addLayout(buttons_layout)
    
    def add_field(self, label: str, widget, required: bool = False):
        """Add a field to the form."""
        if required:
            label = f"{label} *"
        self.form_layout.addRow(label, widget)
    
    def get_field_value(self, field) -> str:
        """Get value from a form field."""
        if isinstance(field, QLineEdit):
            return field.text().strip()
        elif isinstance(field, QComboBox):
            return field.currentText()
        return ""
    
    def set_field_value(self, field, value):
        """Set value in a form field."""
        if isinstance(field, QLineEdit):
            field.setText(str(value) if value else "")
        elif isinstance(field, QComboBox):
            index = field.findText(str(value))
            if index >= 0:
                field.setCurrentIndex(index)
    
    def validate_and_save(self):
        """Validate form and save if valid."""
        try:
            if self.validate():
                data = self.get_data()
                self.save_data(data)
                self.accept()
        except Exception as e:
            QMessageBox.warning(
                self,
                "Erro",
                f"Erro ao salvar: {str(e)}"
            )
    
    def validate(self) -> bool:
        """Validate form data. Override in subclasses."""
        return True
    
    def get_data(self) -> dict:
        """Get form data. Override in subclasses."""
        return {}
    
    def save_data(self, data: dict):
        """Save form data. Override in subclasses."""
        pass