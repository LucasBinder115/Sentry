"""Login view implementation."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFrame, QFormLayout, QMessageBox
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont

class LoginView(QWidget):
    """Simple login view."""
    
    login_attempt = pyqtSignal(dict)  # Emits credentials for validation

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SENTRY - Login")
        self.setFixedSize(400, 300)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the login interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Title
        title = QLabel("SENTRY")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Login form
        form = QFrame()
        form.setStyleSheet("QFrame { background-color: white; border-radius: 10px; }")
        form_layout = QFormLayout(form)
        form_layout.setContentsMargins(20, 20, 20, 20)

        # Username
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Nome de usuário")
        form_layout.addRow("Usuário:", self.username_input)

        # Password
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Senha")
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Senha:", self.password_input)

        layout.addWidget(form)

        # Login button with styling
        self.login_button = QPushButton("Entrar")
        self.login_button.setMinimumHeight(40)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        self.login_button.clicked.connect(self.handle_login)
        layout.addWidget(self.login_button)

        # Error label (hidden by default)
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: red;")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        # Demo credentials hint
        demo_label = QLabel("Demo: usuário=admin, senha=admin")
        demo_label.setAlignment(Qt.AlignCenter)
        demo_label.setStyleSheet("color: gray;")
        layout.addWidget(demo_label)
        
        # Setup enter key handling
        self.username_input.returnPressed.connect(self.password_input.setFocus)
        self.password_input.returnPressed.connect(self.handle_login)
    
    def handle_login(self):
        """Handle login button click."""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            self.show_error("Por favor, preencha todos os campos")
            return
        
        # Clear error if any
        self.clear_error()
        
        # Emit login attempt
        self.login_attempt.emit({
            'username': username,
            'password': password
        })
        
        # Clear password field
        self.password_input.clear()
    
    def show_error(self, message: str):
        """Show error message."""
        self.error_label.setText(message)
        self.error_label.show()
    
    def clear_error(self):
        """Clear error message."""
        self.error_label.hide()
        self.error_label.clear()