# LOGISICA/sentry/ui/views/merchandise_registration_view.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QMessageBox, QFormLayout, QTextEdit, QGroupBox, QComboBox, QDoubleSpinBox,
    QSpinBox, QCheckBox, QProgressBar, QTabWidget, QTableWidget, 
    QTableWidgetItem, QHeaderView, QSplitter, QSizePolicy, QApplication
)
from PyQt5.QtCore import (
    pyqtSignal, QRegExp, Qt, QTimer, pyqtSlot, QDateTime
)
from PyQt5.QtGui import QFont, QDoubleValidator, QIntValidator, QPalette, QColor, QRegExpValidator
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import logging
import re
from decimal import Decimal, InvalidOperation
from sentry.ui.presenters.merchandise_registration_presenter import MerchandiseRegistrationPresenter

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Exceção para erros de validação."""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"Erro no campo '{field}': {message}")

class MerchandiseValidation:
    """Classe para validações de mercadorias."""
    
    PLACA_REGEX = re.compile(r'^[A-Z]{3}-?\d{4}$')
    MIN_WEIGHT = 0.001  # kg
    MAX_WEIGHT = 100000  # kg
    MIN_VOLUME = 0.0001  # m³
    MAX_VOLUME = 1000    # m³
    MAX_DESCRIPTION_LEN = 200
    MAX_NOTES_LEN = 1000
    
    @staticmethod
    def validate_placa(placa: str) -> bool:
        """Valida formato de placa MERCOSUL."""
        cleaned = re.sub(r'[-.\s]', '', placa.upper())
        return bool(MerchandiseValidation.PLACA_REGEX.match(cleaned))
    
    @staticmethod
    def validate_weight(weight_str: str) -> Optional[Decimal]:
        """Valida e converte peso."""
        try:
            weight = Decimal(weight_str.replace(',', '.'))
            if not (MerchandiseValidation.MIN_WEIGHT <= weight <= MerchandiseValidation.MAX_WEIGHT):
                raise ValidationError("weight", f"Peso deve estar entre {MerchandiseValidation.MIN_WEIGHT}kg e {MerchandiseValidation.MAX_WEIGHT}kg")
            return weight
        except (InvalidOperation, ValueError):
            raise ValidationError("weight", "Peso deve ser um número válido (ex: 123.45)")
    
    @staticmethod
    def validate_volume(volume_str: str) -> Optional[Decimal]:
        """Valida e converte volume."""
        try:
            volume = Decimal(volume_str.replace(',', '.'))
            if not (MerchandiseValidation.MIN_VOLUME <= volume <= MerchandiseValidation.MAX_VOLUME):
                raise ValidationError("volume", f"Volume deve estar entre {MerchandiseValidation.MIN_VOLUME}m³ e {MerchandiseValidation.MAX_VOLUME}m³")
            return volume
        except (InvalidOperation, ValueError):
            raise ValidationError("volume", "Volume deve ser um número válido (ex: 1.25)")
    
    @staticmethod
    def validate_description(desc: str) -> bool:
        """Valida descrição."""
        return len(desc.strip()) > 0 and len(desc) <= MerchandiseValidation.MAX_DESCRIPTION_LEN
    
    @staticmethod
    def validate_notes(notes: str) -> bool:
        """Valida observações."""
        return len(notes) <= MerchandiseValidation.MAX_NOTES_LEN

class MerchandiseRegistrationView(QWidget):
    """
    Tela avançada e robusta para cadastro de mercadorias com validações,
    histórico, cálculos automáticos e interface profissional.
    """
    registration_successful = pyqtSignal(dict)  # Emite dados da mercadoria cadastrada
    validation_error = pyqtSignal(str, str)     # field, message
    progress_updated = pyqtSignal(int, str)     # percentage, message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📦 Cadastro de Mercadoria - LOGISICA SENTRY")
        self.setGeometry(200, 200, 800, 600)
        self.setMinimumSize(700, 500)
        
        self.presenter = MerchandiseRegistrationPresenter(self)
        self.registration_in_progress = False
        self.draft_data = {}  # Dados temporários para rascunho
        
        self.setup_ui()
        self.setup_validators()
        self.setup_connections()
        self.load_draft()
        
        logger.info("Tela de cadastro de mercadorias inicializada")
    
    def setup_ui(self):
        """Configura interface moderna e organizada."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header com título e status
        header_layout = self.setup_header()
        main_layout.addLayout(header_layout)
        
        # Splitter principal
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(3)
        
        # Formulário principal
        form_widget = self.setup_form_panel()
        history_widget = self.setup_history_panel()
        
        splitter.addWidget(form_widget)
        splitter.addWidget(history_widget)
        splitter.setSizes([450, 200])
        main_layout.addWidget(splitter)
        
        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        main_layout.addWidget(self.progress_bar)
        
        # Botões de ação
        self.setup_action_buttons(main_layout)
        
        # Status label
        self.status_label = QLabel("👆 Preencha os campos para cadastrar a mercadoria")
        self.status_label.setStyleSheet("color: #6c757d; font-style: italic; padding: 5px;")
        self.status_label.setWordWrap(True)
        main_layout.addWidget(self.status_label)
    
    def setup_header(self) -> QHBoxLayout:
        """Configura header com título e informações."""
        header_layout = QHBoxLayout()
        
        # Título principal
        title_label = QLabel("📦 Cadastro de Mercadoria")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2c3e50; margin-right: 20px;")
        header_layout.addWidget(title_label)
        
        # Info do sistema
        info_label = QLabel(f"ID da Sessão: {QDateTime.currentDateTime().toString('yyyyMMdd-HHmmss')}")
        info_label.setStyleSheet("color: #6c757d; font-size: 10px;")
        header_layout.addWidget(info_label)
        header_layout.addStretch()
        
        return header_layout
    
    def setup_form_panel(self) -> QGroupBox:
        """Configura painel principal do formulário."""
        form_group = QGroupBox("Dados da Mercadoria")
        form_layout = QFormLayout(form_group)
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFormAlignment(Qt.AlignLeft)
        form_layout.setSpacing(10)
        
        # Descrição com autocomplete
        self.input_description = QLineEdit()
        self.input_description.setPlaceholderText("Ex: Carga de eletrônicos frágeis...")
        self.input_description.textChanged.connect(self.on_description_changed)
        form_layout.addRow("🖋️ Descrição*:", self.input_description)
        
        # Dados quantitativos em grupo
        quant_group = QGroupBox("Dimensões e Peso")
        quant_layout = QFormLayout(quant_group)
        
        self.input_weight = QDoubleSpinBox()
        self.input_weight.setRange(0.001, 100000)
        self.input_weight.setDecimals(3)
        self.input_weight.setSuffix(" kg")
        self.input_weight.setSingleStep(0.1)
        self.input_weight.valueChanged.connect(self.on_weight_changed)
        quant_layout.addRow("⚖️ Peso*:", self.input_weight)
        
        self.input_volume = QDoubleSpinBox()
        self.input_volume.setRange(0.0001, 1000)
        self.input_volume.setDecimals(4)
        self.input_volume.setSuffix(" m³")
        self.input_volume.setSingleStep(0.001)
        quant_layout.addRow("📦 Volume*:", self.input_volume)
        
        # Cálculo automático de densidade
        self.density_label = QLabel("Densidade: -- kg/m³")
        self.density_label.setStyleSheet("font-weight: bold; color: #28a745;")
        quant_layout.addRow("📊 Densidade:", self.density_label)
        
        form_layout.addRow(quant_group)
        
        # Veículo
        self.input_vehicle_plate = QLineEdit()
        self.input_vehicle_plate.setPlaceholderText("AAA-1234")
        self.input_vehicle_plate.setInputMask('AAA-9999;_')
        self.input_vehicle_plate.textChanged.connect(self.on_plate_changed)
        form_layout.addRow("🚛 Placa do Veículo:", self.input_vehicle_plate)
        
        # Tipo de mercadoria
        self.combo_merchandise_type = QComboBox()
        self.combo_merchandise_type.addItems([
            "Geral", "Frágil", "Perigosa", "Perecível", "Valiosa", "Congelada"
        ])
        form_layout.addRow("🏷️ Tipo:", self.combo_merchandise_type)
        
        # Observações
        self.input_notes = QTextEdit()
        self.input_notes.setMaximumHeight(80)
        self.input_notes.setPlaceholderText("Observações adicionais, cuidados especiais...")
        form_layout.addRow("📝 Observações:", self.input_notes)
        
        # Opções avançadas
        self.check_fragile = QCheckBox("Marcar como FRÁGIL (atenção especial)")
        self.check_perishable = QCheckBox("Mercadoria PERECÍVEL (controle de temperatura)")
        options_layout = QHBoxLayout()
        options_layout.addWidget(self.check_fragile)
        options_layout.addWidget(self.check_perishable)
        options_layout.addStretch()
        form_layout.addRow(options_layout)
        
        # Validação visual
        self.validation_status = QLabel("✅ Todos os campos válidos")
        self.validation_status.setStyleSheet("color: #28a745; font-weight: bold;")
        form_layout.addRow("Status:", self.validation_status)
        
        return form_group
    
    def setup_history_panel(self) -> QGroupBox:
        """Configura painel de histórico/recentes."""
        history_group = QGroupBox("Mercadorias Recentes")
        history_layout = QVBoxLayout(history_group)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["Descrição", "Peso", "Placa", "Data"])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setMaximumHeight(150)
        self.history_table.itemDoubleClicked.connect(self.on_history_item_clicked)
        history_layout.addWidget(self.history_table)
        
        # Botão para carregar histórico
        load_btn = QPushButton("🔄 Atualizar Histórico")
        load_btn.clicked.connect(self.load_recent_merchandise)
        history_layout.addWidget(load_btn)
        
        return history_group
    
    def setup_action_buttons(self, parent_layout: QVBoxLayout):
        """Configura botões de ação avançados."""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # Salvar rascunho
        self.btn_draft = QPushButton("💾 Salvar Rascunho")
        self.btn_draft.clicked.connect(self.save_draft)
        button_layout.addWidget(self.btn_draft)
        
        # Validar
        self.btn_validate = QPushButton("✅ Validar")
        self.btn_validate.clicked.connect(self.validate_all)
        self.btn_validate.setStyleSheet("QPushButton { background-color: #ffc107; }")
        button_layout.addWidget(self.btn_validate)
        
        # Cadastrar
        self.btn_register = QPushButton("🚀 Cadastrar Mercadoria")
        self.btn_register.clicked.connect(self.on_register_clicked)
        self.btn_register.setStyleSheet("QPushButton { background-color: #28a745; color: white; font-weight: bold; }")
        self.btn_register.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        button_layout.addWidget(self.btn_register)
        
        # Cancelar
        self.btn_cancel = QPushButton("❌ Cancelar")
        self.btn_cancel.clicked.connect(self.cancel_registration)
        self.btn_cancel.setStyleSheet("QPushButton { background-color: #dc3545; color: white; }")
        button_layout.addWidget(self.btn_cancel)
        
        parent_layout.addLayout(button_layout)
    
    def setup_validators(self):
        """Configura validadores avançados para campos."""
        # Validador de placa customizado
        placa_validator = QRegExpValidator(QRegExp(r'^[A-Z]{0,3}-?\d{0,4}$'), self)
        self.input_vehicle_plate.setValidator(placa_validator)
        
        # Conexões de validação em tempo real
        self.input_description.textChanged.connect(self.validate_description)
        self.input_weight.valueChanged.connect(self.validate_weight)
        self.input_volume.valueChanged.connect(self.validate_volume)
        self.input_vehicle_plate.textChanged.connect(self.validate_plate)
    
    def setup_connections(self):
        """Configura todas as conexões de sinal."""
        self.validation_error.connect(self.on_validation_error)
        self.progress_updated.connect(self.on_progress_updated)
        
        # Conexões com presenter
        if hasattr(self.presenter, 'registration_successful'):
            self.presenter.registration_successful.connect(self.registration_successful.emit)
    
    def on_description_changed(self, text: str):
        """Atualiza sugestões baseadas na descrição."""
        if len(text) > 2:
            # Poderia implementar autocomplete com histórico
            pass
        self.validate_description()
    
    def on_weight_changed(self, value: float):
        """Atualiza cálculos quando peso muda."""
        self.update_density()
        self.validate_weight()
    
    def on_plate_changed(self, text: str):
        """Valida placa em tempo real."""
        self.validate_plate()
    
    def validate_description(self):
        """Valida descrição em tempo real."""
        try:
            if not MerchandiseValidation.validate_description(self.input_description.text()):
                raise ValidationError("description", "Descrição obrigatória (máx 200 caracteres)")
            self.input_description.setStyleSheet("border: 2px solid #28a745;")
        except ValidationError as e:
            self.input_description.setStyleSheet("border: 2px solid #dc3545;")
            self.validation_error.emit(e.field, e.message)
    
    def validate_weight(self):
        """Valida peso."""
        try:
            MerchandiseValidation.validate_weight(str(self.input_weight.value()))
            self.input_weight.setStyleSheet("border: 2px solid #28a745;")
        except ValidationError as e:
            self.input_weight.setStyleSheet("border: 2px solid #dc3545;")
    
    def validate_volume(self):
        """Valida volume."""
        try:
            MerchandiseValidation.validate_volume(str(self.input_volume.value()))
            self.input_volume.setStyleSheet("border: 2px solid #28a745;")
        except ValidationError as e:
            self.input_volume.setStyleSheet("border: 2px solid #dc3545;")
    
    def validate_plate(self):
        """Valida placa do veículo."""
        placa = self.input_vehicle_plate.text().upper()
        try:
            if placa and not MerchandiseValidation.validate_placa(placa):
                raise ValidationError("vehicle_plate", "Formato inválido. Use: AAA-1234")
            self.input_vehicle_plate.setStyleSheet("border: 2px solid #28a745;" if placa else "")
        except ValidationError as e:
            self.input_vehicle_plate.setStyleSheet("border: 2px solid #dc3545;")
            self.validation_error.emit(e.field, e.message)
    
    def validate_all(self) -> bool:
        """Valida todos os campos obrigatórios."""
        errors = []
        
        # Validações obrigatórias
        if not self.input_description.text().strip():
            errors.append("Descrição é obrigatória")
        if self.input_weight.value() <= 0:
            errors.append("Peso deve ser maior que zero")
        if self.input_volume.value() <= 0:
            errors.append("Volume deve ser maior que zero")
        
        if errors:
            self.show_validation_error("\n".join(errors))
            return False
        
        self.status_label.setText("✅ Todos os campos válidos - pronto para cadastrar!")
        return True
    
    def update_density(self):
        """Calcula densidade automaticamente."""
        weight = self.input_weight.value()
        volume = self.input_volume.value()
        if volume > 0:
            density = weight / volume
            self.density_label.setText(f"Densidade: {density:.1f} kg/m³")
        else:
            self.density_label.setText("Densidade: -- kg/m³")
    
    def on_register_clicked(self):
        """Inicia cadastro com validação completa."""
        if not self.validate_all():
            return
        
        if self.registration_in_progress:
            self.show_warning("Cadastro já em andamento!")
            return
        
        merchandise_data = self.get_merchandise_data()
        
        self.start_registration(merchandise_data)
    
    def get_merchandise_data(self) -> Dict[str, Any]:
        """Coleta e formata dados da mercadoria."""
        placa = self.input_vehicle_plate.text().replace('-', '').upper().strip()
        
        return {
            "description": self.input_description.text().strip(),
            "weight": float(self.input_weight.value()),
            "volume": float(self.input_volume.value()),
            "vehicle_plate": placa if placa else None,
            "merchandise_type": self.combo_merchandise_type.currentText(),
            "notes": self.input_notes.toPlainText().strip(),
            "is_fragile": self.check_fragile.isChecked(),
            "is_perishable": self.check_perishable.isChecked(),
            "density": self.input_weight.value() / self.input_volume.value() if self.input_volume.value() > 0 else None,
            "created_at": datetime.now().isoformat(),
            "status": "PENDING"  # Para workflow posterior
        }
    
    def start_registration(self, data: Dict[str, Any]):
        """Inicia processo de cadastro com feedback visual."""
        self.registration_in_progress = True
        self.btn_register.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("⏳ Cadastrando mercadoria...")
        
        self.progress_updated.emit(10, "Validando dados...")
        
        try:
            QTimer.singleShot(500, lambda: self.presenter.register_merchandise(data))
        except Exception as e:
            logger.error(f"Erro ao iniciar cadastro: {e}")
            self.show_error(f"Erro inesperado: {str(e)}")
            self.cancel_registration()
    
    @pyqtSlot(int, str)
    def on_progress_updated(self, percentage: int, message: str):
        """Atualiza progresso do cadastro."""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(f"⏳ {message}")
        
        if percentage >= 100:
            self.registration_successful.emit(self.draft_data)
    
    def cancel_registration(self):
        """Cancela operação em andamento."""
        self.registration_in_progress = False
        self.btn_register.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("❌ Operação cancelada")
        logger.info("Cadastro de mercadoria cancelado")
    
    def save_draft(self):
        """Salva rascunho dos dados."""
        self.draft_data = self.get_merchandise_data()
        # Salvar em arquivo/configuração persistente
        logger.info("Rascunho salvo")
        self.show_info("Rascunho salvo com sucesso!")
    
    def load_draft(self):
        """Carrega rascunho salvo."""
        # Simular carregamento de rascunho
        pass
    
    def load_recent_merchandise(self):
        """Carrega histórico recente (simulado)."""
        # Implementar chamada ao presenter para histórico
        self.history_table.setRowCount(3)
        for i in range(3):
            self.history_table.setItem(i, 0, QTableWidgetItem(f"Item {i+1}"))
            self.history_table.setItem(i, 1, QTableWidgetItem("150.5 kg"))
            self.history_table.setItem(i, 2, QTableWidgetItem("ABC-1234"))
            self.history_table.setItem(i, 3, QTableWidgetItem("2025-01-15"))
    
    def on_history_item_clicked(self, item):
        """Carrega dados do histórico no formulário."""
        # Implementar lógica de preenchimento automático
        pass
    
    @pyqtSlot(str, str)
    def on_validation_error(self, field: str, message: str):
        """Trata erros de validação."""
        self.show_validation_error(f"{message} (Campo: {field})")
        self.status_label.setText("❌ Erro de validação detectado")
    
    # Métodos de feedback visual
    def show_success(self, message: str, data: Optional[Dict] = None):
        """Exibe sucesso com detalhes."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("✅ Cadastro Realizado")
        msg.setText("Mercadoria cadastrada com sucesso!")
        msg.setDetailedText(f"{message}\n\nID: {data.get('id', 'N/A') if data else 'N/A'}")
        msg.exec_()
        
        self.registration_successful.emit(data or {})
        self.close()
    
    def show_error(self, message: str):
        """Exibe erro crítico."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("❌ Erro no Cadastro")
        msg.setText("Falha no cadastro da mercadoria")
        msg.setDetailedText(message)
        msg.exec_()
        
        self.status_label.setText("❌ Erro no cadastro")
        logger.error(f"Erro de cadastro: {message}")
    
    def show_warning(self, message: str):
        """Exibe aviso."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("⚠️ Aviso")
        msg.setText(message)
        msg.exec_()
    
    def show_info(self, message: str):
        """Exibe informação."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("ℹ️ Informação")
        msg.setText(message)
        msg.exec_()
    
    def show_validation_error(self, message: str):
        """Exibe erro de validação."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("❌ Validação")
        msg.setText("Dados inválidos:")
        msg.setDetailedText(message)
        msg.exec_()
    
    def closeEvent(self, event):
        """Gerencia fechamento da janela."""
        if self.registration_in_progress:
            reply = QMessageBox.question(
                self, "Confirmar", 
                "Cadastro em andamento. Deseja cancelar?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.cancel_registration()
                # Salvar rascunho automaticamente
                self.save_draft()
                event.accept()
            else:
                event.ignore()
        else:
            self.save_draft()
            event.accept()
    
    def keyPressEvent(self, event):
        """Atalhos de teclado."""
        if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            if self.btn_register.isEnabled():
                self.on_register_clicked()
        elif event.key() == Qt.Key_Escape:
            self.cancel_registration()
        super().keyPressEvent(event)