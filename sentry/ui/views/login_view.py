"""Modern login view implementation with centered design."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFrame, QFormLayout, QMessageBox,
    QHBoxLayout, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import pyqtSignal, Qt, QPoint
from PyQt5.QtGui import QFont, QColor, QIcon

class LoginView(QWidget):
    """Modern centered login view with shadow effects."""
    
    login_attempt = pyqtSignal(dict)  # Emits credentials for validation

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SENTRY - Login")
        self.setFixedSize(800, 600)  # Larger window for better presentation
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
            }
        """)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the modern login interface."""
        # Main layout with center alignment
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Center container
        center_widget = QWidget()
        center_widget.setFixedWidth(400)
        center_layout = QVBoxLayout(center_widget)
        center_layout.setSpacing(30)
        center_layout.setContentsMargins(40, 60, 40, 40)
        
        # Logo and title container
        title_container = QFrame()
        title_container.setStyleSheet("background: transparent;")
        title_layout = QVBoxLayout(title_container)
        
        # Title
        title = QLabel("SENTRY")
        title.setFont(QFont("Arial", 32, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2c3e50;")
        title_layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Sistema de Controle Logístico")
        subtitle.setFont(QFont("Arial", 12))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #7f8c8d; margin-top: -10px;")
        title_layout.addWidget(subtitle)
        
        center_layout.addWidget(title_container)

        # Login form container with shadow
        form_container = QFrame()
        form_container.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
        """)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 2)
        form_container.setGraphicsEffect(shadow)
        
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(30, 30, 30, 30)
        form_layout.setSpacing(20)

        # Username input with icon
        username_container = QFrame()
        username_container.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        username_layout = QHBoxLayout(username_container)
        username_layout.setContentsMargins(10, 5, 10, 5)
        
        username_icon = QLabel("👤")
        username_layout.addWidget(username_icon)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Digite seu usuário")
        self.username_input.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                padding: 5px;
                font-size: 14px;
            }
        """)
        username_layout.addWidget(self.username_input)
        
        form_layout.addWidget(username_container)

        # Password input with icon
        password_container = QFrame()
        password_container.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        password_layout = QHBoxLayout(password_container)
        password_layout.setContentsMargins(10, 5, 10, 5)
        
        password_icon = QLabel("🔒")
        password_layout.addWidget(password_icon)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Digite sua senha")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                padding: 5px;
                font-size: 14px;
            }
        """)
        password_layout.addWidget(self.password_input)
        
        form_layout.addWidget(password_container)

        # Login button with modern styling
        self.login_button = QPushButton("Entrar no Sistema")
        self.login_button.setMinimumHeight(45)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:pressed {
                background-color: #219a52;
            }
        """)
        self.login_button.setCursor(Qt.PointingHandCursor)
        self.login_button.clicked.connect(self.handle_login)
        form_layout.addWidget(self.login_button)

        # Error label with improved styling
        self.error_label = QLabel()
        self.error_label.setStyleSheet("""
            QLabel {
                color: #e74c3c;
                padding: 10px;
                background-color: #fde8e7;
                border-radius: 5px;
                font-size: 13px;
            }
        """)
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.hide()
        form_layout.addWidget(self.error_label)

        # Add form container to center layout
        center_layout.addWidget(form_container)

        # Demo credentials hint with improved styling
        demo_container = QFrame()
        demo_container.setStyleSheet("background: transparent;")
        demo_layout = QVBoxLayout(demo_container)
        
        demo_label = QLabel("🔑 Credenciais de demonstração:")
        demo_label.setAlignment(Qt.AlignCenter)
        demo_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        demo_layout.addWidget(demo_label)
        
        credentials_label = QLabel("usuário: <b>admin</b> • senha: <b>admin</b>")
        credentials_label.setAlignment(Qt.AlignCenter)
        credentials_label.setStyleSheet("color: #95a5a6; font-size: 12px;")
        demo_layout.addWidget(credentials_label)
        
        center_layout.addWidget(demo_container)
        
        # Add the center container to main layout
        main_layout.addStretch()
        main_layout.addWidget(center_widget)
        main_layout.addStretch()
        
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