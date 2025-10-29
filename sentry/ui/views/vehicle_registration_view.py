"""Vehicle registration view implementation."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFormLayout, QFrame, QShortcut
)
from PyQt5.QtCore import pyqtSignal, Qt, QRegExp
from PyQt5.QtGui import QFont, QRegExpValidator, QKeySequence

class VehicleRegistrationView(QWidget):
    """View for registering new vehicles."""
    
    # Signals
    registration_successful = pyqtSignal(dict)
    back_to_dashboard = pyqtSignal()

    def __init__(self, parent=None):
        """Initialize the vehicle registration view."""
        super().__init__(parent)
        self.setWindowTitle("Cadastro de Veículo")
        self.setMinimumWidth(500)
        self._setup_ui()
        self._setup_shortcuts()

    def _setup_ui(self):
        """Setup the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Cadastro de Veículo")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Form container with border
        form_container = QFrame()
        form_container.setFrameStyle(QFrame.StyledPanel)
        form_container.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 5px;
            }
        """)
        
        form_layout = QFormLayout(form_container)
        form_layout.setSpacing(15)
        form_layout.setContentsMargins(20, 20, 20, 20)

        # Plate input with validator
        self.input_plate = QLineEdit()
        self.input_plate.setPlaceholderText("ABC1D23")
        plate_validator = QRegExpValidator(QRegExp("[A-Za-z]{3}[0-9][A-Za-z0-9][0-9]{2}"))
        self.input_plate.setValidator(plate_validator)
        self.input_plate.setMaxLength(7)
        form_layout.addRow("Placa do Veículo:*", self.input_plate)

        # Model input
        self.input_model = QLineEdit()
        self.input_model.setPlaceholderText("Ex: Mercedes-Benz 2544")
        form_layout.addRow("Modelo:*", self.input_model)

        # Color input
        self.input_color = QLineEdit()
        self.input_color.setPlaceholderText("Ex: Branco")
        form_layout.addRow("Cor:", self.input_color)

        main_layout.addWidget(form_container)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.back_btn = QPushButton("← Voltar")
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        self.back_btn.clicked.connect(self._on_back_clicked)

        self.register_btn = QPushButton("Cadastrar Veículo")
        self.register_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.register_btn.clicked.connect(self._on_register_clicked)

        button_layout.addWidget(self.back_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.register_btn)

        main_layout.addLayout(button_layout)
        main_layout.addStretch()

        # Set focus to plate input
        self.input_plate.setFocus()

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        # Esc to go back
        self.back_shortcut = QShortcut(QKeySequence.Cancel, self)
        self.back_shortcut.activated.connect(self._on_back_clicked)
        
        # Enter/Return to register
        self.register_shortcut = QShortcut(QKeySequence.InsertParagraphSeparator, self)
        self.register_shortcut.activated.connect(self._on_register_clicked)

    def _validate_inputs(self) -> bool:
        """Validate form inputs."""
        plate = self.input_plate.text().strip()
        if not plate:
            self.show_error("A placa do veículo é obrigatória.")
            self.input_plate.setFocus()
            return False
            
        if len(plate) != 7:
            self.show_error("A placa deve ter exatamente 7 caracteres.")
            self.input_plate.setFocus()
            return False

        model = self.input_model.text().strip()
        if not model:
            self.show_error("O modelo do veículo é obrigatório.")
            self.input_model.setFocus()
            return False

        return True

    def _on_register_clicked(self):
        """Handle register button click."""
        if not self._validate_inputs():
            return

        vehicle_data = {
            "plate": self.input_plate.text().strip().upper(),
            "model": self.input_model.text().strip(),
            "color": self.input_color.text().strip()
        }

        self.registration_successful.emit(vehicle_data)

    def _on_back_clicked(self):
        """Handle back button click."""
        self.back_to_dashboard.emit()

    def show_error(self, message: str):
        """Show error message."""
        QMessageBox.warning(self, "Erro", message)

    def show_success(self, message: str):
        """Show success message."""
        QMessageBox.information(self, "Sucesso", message)

    def clear_form(self):
        """Clear all form inputs."""
        self.input_plate.clear()
        self.input_model.clear()
        self.input_color.clear()
        self.input_plate.setFocus()
