"""Dashboard view implementation."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QTableWidget, QTableWidgetItem,
    QSplitter, QComboBox, QMessageBox, QMainWindow
)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont

from .vehicles_view import VehiclesView
from .merchandise_view import MerchandiseView
from .carrier_view import CarrierView

class DashboardView(QWidget):
    """Main dashboard view."""
    
    # Navigation signals
    logout = pyqtSignal()

    def __init__(self, user_data: dict):
        """Initialize the dashboard view."""
        super().__init__()
        self.user_data = user_data
        
        # Initialize UI
        self.setWindowTitle("SENTRY - Dashboard")
        self._setup_ui()

    def _setup_ui(self):
        """Setup the dashboard interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header with user info and logout
        header = QFrame()
        header.setStyleSheet("QFrame { background-color: #f8f9fa; border-radius: 5px; }")
        header_layout = QHBoxLayout(header)
        
        user_label = QLabel(f"Bem-vindo, {self.user_data.get('username', 'Usuário')}")
        user_label.setFont(QFont("Arial", 14))
        header_layout.addWidget(user_label)
        
        # Spacer
        header_layout.addStretch()
        
        # Logout button
        logout_btn = QPushButton("Sair")
        logout_btn.clicked.connect(self.logout.emit)
        header_layout.addWidget(logout_btn)
        
        layout.addWidget(header)
        
        # Navigation buttons
        nav_frame = QFrame()
        nav_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 20px;
            }
        """)
        nav_layout = QVBoxLayout(nav_frame)
        
        # Navigation title
        nav_title = QLabel("Menu Principal")
        nav_title.setFont(QFont("Arial", 16, QFont.Bold))
        nav_title.setAlignment(Qt.AlignCenter)
        nav_layout.addWidget(nav_title)
        
        # Create navigation buttons
        buttons_data = [
            ("🚗 Veículos", "Gerenciar veículos e placas"),
            ("📦 Mercadorias", "Controle de mercadorias"),
            ("🏭 Transportadoras", "Gerenciar transportadoras"),
            ("📝 Registros", "Histórico de acessos"),
        ]
        
        for icon_text, description in buttons_data:
            # Button container for better styling
            button_container = QFrame()
            button_layout = QVBoxLayout(button_container)
            button_layout.setSpacing(5)
            
            # Create styled button
            button = QPushButton(icon_text)
            button.setMinimumHeight(50)
            button.setFont(QFont("Arial", 12))
            button.setStyleSheet("""
                QPushButton {
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 5px;
                    padding: 10px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #e9ecef;
                }
            """)
            
            # Add description label
            desc_label = QLabel(description)
            desc_label.setStyleSheet("color: #6c757d; padding-left: 5px;")
            
            # Add to container
            button_layout.addWidget(button)
            button_layout.addWidget(desc_label)
            
            # Connect button signal
            button_name = icon_text.split()[1].lower()
            button.setObjectName(button_name)
            button.clicked.connect(self._handle_navigation)
            
            # Add to navigation layout
            nav_layout.addWidget(button_container)
            
        # Add navigation frame to main layout
        layout.addWidget(nav_frame, 1)
        
    def _handle_navigation(self):
        """Handle navigation button clicks."""
        sender = self.sender()
        if not sender:
            return
            
        button_name = sender.objectName()
        
        try:
            # Create appropriate view based on button
            view = None
            if button_name == "veículos":
                view = VehiclesView(self)
            elif button_name == "mercadorias":
                view = MerchandiseView(self)
            elif button_name == "transportadoras":
                view = CarrierView(self)
            elif button_name == "registros":
                QMessageBox.information(
                    self,
                    "Em Desenvolvimento",
                    "Sistema de registros em desenvolvimento."
                )
                return
            
            if view:
                # Create new window for the view
                window = QMainWindow(self)
                window.setCentralWidget(view)
                window.resize(800, 600)
                window.show()
                
        except Exception as e:
            QMessageBox.warning(
                self,
                "Erro",
                f"Erro ao abrir seção: {str(e)}"
            )