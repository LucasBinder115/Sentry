# sentry/ui/widgets/vehicle_query_widget.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QTextEdit
from PyQt5.QtCore import pyqtSignal, Qt

class VehicleQueryWidget(QWidget):
    """
    Widget para consulta de segurança de veículos pela placa.
    """
    # Sinal emitido quando o usuário clica em consultar.
    # Ele carrega a string da placa como argumento.
    query_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Campo de entrada da placa
        self.plate_input = QLineEdit()
        self.plate_input.setPlaceholderText("Digite a placa (ex: ABC1234)")
        # Permite que a tecla Enter também dispare a consulta
        self.plate_input.returnPressed.connect(self.on_query_clicked)
        layout.addWidget(self.plate_input)

        # Botão de consulta
        self.query_button = QPushButton("Consultar Segurança")
        self.query_button.clicked.connect(self.on_query_clicked)
        layout.addWidget(self.query_button)

        # Área de exibição de resultados
        self.results_display = QTextEdit()
        self.results_display.setReadOnly(True)
        self.results_display.setPlaceholderText("O resultado da consulta aparecerá aqui...")
        layout.addWidget(self.results_display)

    def on_query_clicked(self):
        """Método chamado quando o botão ou Enter é pressionado."""
        plate = self.plate_input.text().strip().upper()
        if plate:
            # Emite o sinal com o texto da placa
            self.query_requested.emit(plate)
            
    def display_results(self, text: str):
        """Método público para o Presenter atualizar os resultados."""
        self.results_display.setText(text)

    def set_loading(self, is_loading: bool):
        """Método público para o Presenter controlar o estado do botão."""
        self.query_button.setEnabled(not is_loading)
        if is_loading:
            self.query_button.setText("Consultando...")
        else:
            self.query_button.setText("Consultar Segurança")