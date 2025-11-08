"""Carrier registration view implementation."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, 
    QPushButton, QFrame, QHBoxLayout, QMessageBox
)
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtCore import QRegExp

class CarrierRegistrationView(QWidget):
    """Simple carrier registration view."""
    
    registration_successful = pyqtSignal(dict)
    back_to_dashboard = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cadastro de Transportadora")
        self.setMinimumWidth(500)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the registration interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Form container
        form = QFrame()
        form.setStyleSheet("QFrame { background-color: white; border-radius: 10px; }")
        form_layout = QFormLayout(form)
        form_layout.setContentsMargins(20, 20, 20, 20)

        # Fields
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nome da empresa")
        form_layout.addRow("Nome:*", self.name_input)

        self.cnpj_input = QLineEdit()
        self.cnpj_input.setPlaceholderText("00.000.000/0000-00")
        # Allow only digits, max 14
        self.cnpj_input.setValidator(QRegExpValidator(QRegExp("^\\d{0,14}$"), self))
        self.cnpj_input.setMaxLength(14)
        form_layout.addRow("CNPJ:*", self.cnpj_input)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("(00) 00000-0000")
        # Allow only digits, max 11
        self.phone_input.setValidator(QRegExpValidator(QRegExp("^\\d{0,11}$"), self))
        self.phone_input.setMaxLength(11)
        form_layout.addRow("Telefone:", self.phone_input)

        layout.addWidget(form)

        # Buttons
        button_layout = QHBoxLayout()
        
        back_btn = QPushButton("← Voltar")
        back_btn.clicked.connect(self.back_to_dashboard.emit)
        
        register_btn = QPushButton("Cadastrar")
        register_btn.setStyleSheet("background-color: #28a745; color: white;")
        register_btn.clicked.connect(self._handle_registration)
        
        button_layout.addWidget(back_btn)
        button_layout.addStretch()
        button_layout.addWidget(register_btn)
        
        layout.addLayout(button_layout)

    def _handle_registration(self):
        """Handle registration attempt."""
        # Basic validation
        name = self.name_input.text().strip()
        cnpj = self.cnpj_input.text().strip()
        phone = self.phone_input.text().strip()
        # Sanitize: keep only digits (validators already enforce, but double-sanitize)
        cnpj = ''.join(ch for ch in cnpj if ch.isdigit())[:14]
        phone = ''.join(ch for ch in phone if ch.isdigit())[:11]
        
        if not name or not cnpj:
            QMessageBox.warning(self, "Erro", "Nome e CNPJ são obrigatórios")
            return

        # Emit data for presenter
        self.registration_successful.emit({
            "name": name,
            "cnpj": cnpj,
            "phone": phone
        })
