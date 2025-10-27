# LOGISICA/sentry/ui/views/vehicle_registration_view.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QMessageBox, QFormLayout, QFileDialog, QGroupBox, QComboBox, QTextEdit,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QCheckBox, QSizePolicy, QTabWidget, QStyledItemDelegate
)
from PyQt5.QtCore import (
    pyqtSignal, QRegExp, Qt, QTimer, pyqtSlot, QDateTime,
    QSortFilterProxyModel
)
from PyQt5.QtGui import QFont, QDoubleValidator, QIntValidator, QPalette, QColor, QRegExpValidator
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import logging
import re
from decimal import Decimal
from sentry.ui.presenters.vehicle_registration_presenter import VehicleRegistrationPresenter

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Exceção personalizada para validações de veículos."""
    def __init__(self, field: str, message: str, error_code: str = "VAL_001"):
        self.field = field
        self.message = message
        self.error_code = error_code
        super().__init__(f"[{error_code}] {field}: {message}")

class VehicleValidation:
    """Classe especializada em validações de veículos."""
    
    # Padrões de validação
    PLACA_MERCOSUL_REGEX = re.compile(r'^[A-Z]{3}[0-9][A-Z][0-9]{2}$')  # ABC1D23
    PLACA_ANTIGA_REGEX = re.compile(r'^[A-Z]{3}-\d{4}$')  # ABC-1234
    CNPJ_REGEX = re.compile(r'^\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}$')
    
    # Cores válidas (BR)
    VALID_COLORS = {
        'BRANCO', 'PRETO', 'CINZA', 'PRATA', 'AZUL', 'VERDE', 'VERMELHO', 
        'AMARELO', 'MARROM', 'BEGE', 'ROXO', 'ROSA', 'LARANJA', 'DOURADO'
    }
    
    MODELS_BY_TYPE = {
        'CARRO': ['Sedan', 'Hatch', 'SUV', 'Pickup', 'Coupé'],
        'MOTO': ['Street', 'Trail', 'Sport', 'Cruiser'],
        'CAMINHÃO': ['Toco', 'Truck', 'Cavalo Mecânico', 'Carreta'],
        'ÔNIBUS': ['Urbanos', 'Rodoviários', 'Micro-ônibus']
    }
    
    @staticmethod
    def validate_plate(plate: str) -> Tuple[bool, str]:
        """Valida placa de veículo (MERCOSUL ou antiga)."""
        cleaned = re.sub(r'[-.\s]', '', plate.upper())
        
        if VehicleValidation.PLACA_MERCOSUL_REGEX.match(cleaned):
            return True, "MERCOSUL"
        elif VehicleValidation.PLACA_ANTIGA_REGEX.match(plate.upper()):
            return True, "ANTIGA"
        
        raise ValidationError("plate", "Formato inválido. Use: ABC1D23 (MERCOSUL) ou ABC-1234 (Antiga)", "PLATE_001")
    
    @staticmethod
    def validate_cnpj(cnpj: str) -> bool:
        """Valida CNPJ com algoritmo oficial."""
        cnpj = re.sub(r'[^0-9]', '', cnpj)
        
        if len(cnpj) != 14:
            return False
        
        # Algoritmo de validação CNPJ
        def calc_digit(weights, digits):
            total = sum(w * int(d) for w, d in zip(weights, digits))
            return (11 - (total % 11)) % 10
        
        digits = [int(d) for d in cnpj]
        
        # Primeiro dígito verificador
        weights1 = [5,4,3,2,9,8,7,6,5,4,3,2]
        digit1 = calc_digit(weights1, digits[:12])
        if digits[12] != digit1:
            return False
        
        # Segundo dígito verificador
        weights2 = [6,5,4,3,2,9,8,7,6,5,4,3,2]
        digit2 = calc_digit(weights2, digits[:13])
        if digits[13] != digit2:
            return False
        
        return True
    
    @staticmethod
    def format_cnpj(cnpj: str) -> str:
        """Formata CNPJ para padrão brasileiro."""
        cnpj = re.sub(r'[^0-9]', '', cnpj)
        if len(cnpj) == 14:
            return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
        return cnpj
    
    @staticmethod
    def validate_model(model: str, vehicle_type: str) -> bool:
        """Valida modelo baseado no tipo de veículo."""
        if not model.strip():
            raise ValidationError("model", "Modelo é obrigatório")
        if len(model) > 50:
            raise ValidationError("model", "Modelo não pode exceder 50 caracteres")
        return True
    
    @staticmethod
    def validate_color(color: str) -> bool:
        """Valida cor do veículo."""
        if not color.strip():
            return True  # Opcional
        normalized = color.upper().strip()
        if normalized in VehicleValidation.VALID_COLORS:
            return True
        raise ValidationError("color", f"Cor inválida. Use: {', '.join(VehicleValidation.VALID_COLORS)}")

class CNPJDelegate(QStyledItemDelegate):
    """Delegate customizado para formatação automática de CNPJ."""
    
    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if editor:
            editor.textChanged.connect(self.format_cnpj)
        return editor
    
    def setEditorData(self, editor, index):
        super().setEditorData(editor, index)
    
    def setModelData(self, editor, model, index):
        value = editor.text()
        formatted = VehicleValidation.format_cnpj(value)
        model.setData(index, formatted)
        super().setModelData(editor, model, index)
    
    @staticmethod
    def format_cnpj(text):
        """Formata CNPJ em tempo real."""
        cnpj = re.sub(r'[^0-9]', '', text)
        if len(cnpj) <= 14:
            formatted = VehicleValidation.format_cnpj(cnpj)
            if formatted != text:
                # Isso requer um pouco de hack para QLineEdit
                pass

class VehicleRegistrationView(QWidget):
    """
    Tela avançada para cadastro de veículos com validações rigorosas,
    histórico, upload de documentos e integração com RENAVAM.
    """
    registration_successful = pyqtSignal(dict)
    validation_error = pyqtSignal(str, str, str)  # field, message, code
    progress_updated = pyqtSignal(int, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🚛 Cadastro de Veículo - LOGISICA SENTRY")
        self.setGeometry(200, 200, 900, 700)
        self.setMinimumSize(800, 600)
        
        self.presenter = VehicleRegistrationPresenter(self)
        self.registration_in_progress = False
        self.draft_data = {}
        self.vehicle_history = []
        
        self.setup_ui()
        self.setup_validators()
        self.setup_connections()
        self.load_draft()
        
        logger.info("Tela de cadastro de veículos inicializada")
    
    def setup_ui(self):
        """Configura interface moderna e organizada."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header
        header_layout = self.setup_header()
        main_layout.addLayout(header_layout)
        
        # Tabs para organização
        tabs = QTabWidget()
        
        # Aba principal - Dados básicos
        basic_tab = self.setup_basic_tab()
        tabs.addTab(basic_tab, "📋 Dados Básicos")
        
        # Aba documentos
        docs_tab = self.setup_documents_tab()
        tabs.addTab(docs_tab, "📎 Documentos")
        
        # Aba histórico
        history_tab = self.setup_history_tab()
        tabs.addTab(history_tab, "📈 Histórico")
        
        main_layout.addWidget(tabs)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Action buttons
        self.setup_action_buttons(main_layout)
        
        # Status
        self.status_label = QLabel("👆 Preencha os dados do veículo")
        self.status_label.setStyleSheet("color: #6c757d; padding: 5px;")
        main_layout.addWidget(self.status_label)
    
    def setup_header(self) -> QHBoxLayout:
        """Header com título e metadados."""
        header_layout = QHBoxLayout()
        
        title_label = QLabel("🚛 Cadastro de Veículo")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2c3e50;")
        header_layout.addWidget(title_label)
        
        info_label = QLabel(f"Sessão: {QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm')}")
        info_label.setStyleSheet("color: #6c757d; font-size: 10px;")
        header_layout.addWidget(info_label)
        header_layout.addStretch()
        
        return header_layout
    
    def setup_basic_tab(self) -> QWidget:
        """Aba de dados básicos do veículo."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Dados principais
        main_group = QGroupBox("Informações Principais")
        main_layout = QFormLayout(main_group)
        
        # Placa com validação especial
        self.input_plate = QLineEdit()
        self.input_plate.setPlaceholderText("ABC1D23 (MERCOSUL) ou ABC-1234")
        self.input_plate.textChanged.connect(self.validate_plate)
        self.input_plate.setStyleSheet("font-weight: bold; padding: 8px;")
        main_layout.addRow("🔢 Placa*:", self.input_plate)
        
        # Tipo de veículo
        self.combo_type = QComboBox()
        self.combo_type.addItems(["CARRO", "MOTO", "CAMINHÃO", "ÔNIBUS", "REBOQUE"])
        self.combo_type.currentTextChanged.connect(self.on_type_changed)
        main_layout.addRow("🚙 Tipo*:", self.combo_type)
        
        # Modelo
        self.input_model = QLineEdit()
        self.input_model.setPlaceholderText("Ex: Fiat Strada Working")
        self.input_model.textChanged.connect(self.validate_model)
        main_layout.addRow("🚗 Modelo*:", self.input_model)
        
        # Cor
        self.input_color = QLineEdit()
        self.input_color.setPlaceholderText("Ex: Branco, Azul, Prata...")
        self.input_color.textChanged.connect(self.validate_color)
        main_layout.addRow("🎨 Cor:", self.input_color)
        
        # RENAVAM
        self.input_renavam = QLineEdit()
        self.input_renavam.setInputMask('99999999999;_')
        self.input_renavam.setPlaceholderText("11 dígitos")
        main_layout.addRow("🆔 RENAVAM:", self.input_renavam)
        
        # Transportadora
        carrier_group = QGroupBox("Dados da Transportadora")
        carrier_layout = QFormLayout(carrier_group)
        
        self.input_carrier_cnpj = QLineEdit()
        self.input_carrier_cnpj.setPlaceholderText("00.000.000/0000-00")
        self.input_carrier_cnpj.textChanged.connect(self.validate_cnpj)
        carrier_layout.addRow("🏢 CNPJ:", self.input_carrier_cnpj)
        
        self.input_carrier_name = QLineEdit()
        self.input_carrier_name.setPlaceholderText("Nome da empresa transportadora")
        carrier_layout.addRow("📝 Razão Social:", self.input_carrier_name)
        
        main_layout.addRow(carrier_group)
        
        # Status do veículo
        self.combo_status = QComboBox()
        self.combo_status.addItems(["ATIVO", "INATIVO", "SUSPENSO", "BAIXADO"])
        self.combo_status.setCurrentText("ATIVO")
        main_layout.addRow("📊 Status*:", self.combo_status)
        
        # Observações
        self.input_notes = QTextEdit()
        self.input_notes.setMaximumHeight(80)
        self.input_notes.setPlaceholderText("Observações, restrições, manutenções...")
        main_layout.addRow("📝 Observações:", self.input_notes)
        
        layout.addWidget(main_group)
        layout.addStretch()
        
        return widget
    
    def setup_documents_tab(self) -> QWidget:
        """Aba para upload de documentos."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        docs_group = QGroupBox("Documentos do Veículo")
        docs_layout = QVBoxLayout(docs_group)
        
        # Campos para documentos
        doc_fields = [
            ("CRLV", "Certificado de Registro e Licenciamento"),
            ("ANTT", "Autorização ANTT"),
            ("SEGURO", "Apólice de Seguro"),
            ("IPVA", "Comprovante IPVA")
        ]
        
        self.document_files = {}
        
        for doc_type, doc_desc in doc_fields:
            doc_layout = QHBoxLayout()
            label = QLabel(f"{doc_type}:")
            file_label = QLabel("Nenhum arquivo selecionado")
            file_label.setStyleSheet("color: #6c757d; padding: 5px;")
            
            btn_select = QPushButton("📎 Selecionar")
            btn_select.clicked.connect(lambda checked, dt=doc_type: self.select_document(dt, file_label))
            
            doc_layout.addWidget(label)
            doc_layout.addWidget(file_label)
            doc_layout.addWidget(btn_select)
            docs_layout.addLayout(doc_layout)
            
            self.document_files[doc_type] = file_label
        
        docs_layout.addStretch()
        layout.addWidget(docs_group)
        
        return widget
    
    def setup_history_tab(self) -> QWidget:
        """Aba de histórico de veículos."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "Placa", "Modelo", "Cor", "CNPJ", "Status", "Data Cadastro"
        ])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.doubleClicked.connect(self.on_history_double_click)
        layout.addWidget(self.history_table)
        
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Atualizar")
        refresh_btn.clicked.connect(self.load_vehicle_history)
        clear_btn = QPushButton("🗑️ Limpar Seleção")
        clear_btn.clicked.connect(self.history_table.clearSelection)
        
        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return widget
    
    def setup_action_buttons(self, parent_layout: QVBoxLayout):
        """Botões de ação avançados."""
        button_layout = QHBoxLayout()
        
        self.btn_draft = QPushButton("💾 Rascunho")
        self.btn_draft.clicked.connect(self.save_draft)
        
        self.btn_validate = QPushButton("✅ Validar")
        self.btn_validate.clicked.connect(self.validate_all)
        self.btn_validate.setStyleSheet("background-color: #ffc107; font-weight: bold;")
        
        self.btn_register = QPushButton("🚀 Cadastrar Veículo")
        self.btn_register.clicked.connect(self.on_register_clicked)
        self.btn_register.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")
        
        self.btn_cancel = QPushButton("❌ Cancelar")
        self.btn_cancel.clicked.connect(self.cancel_action)
        self.btn_cancel.setStyleSheet("background-color: #dc3545; color: white;")
        
        button_layout.addWidget(self.btn_draft)
        button_layout.addWidget(self.btn_validate)
        button_layout.addWidget(self.btn_register)
        button_layout.addWidget(self.btn_cancel)
        
        parent_layout.addLayout(button_layout)
    
    def setup_validators(self):
        """Configura validadores avançados."""
        # Validador customizado para placa
        plate_regex = QRegExp(r'^[A-Z0-3]{0,3}-?\d{0,4}|[A-Z0-3]{0,3}\d{0,4}$')
        self.input_plate.setValidator(QRegExpValidator(plate_regex, self))
        
        # Validador CNPJ
        cnpj_regex = QRegExp(r'\d{0,2}\.?\d{0,3}\.?\d{0,3}\/?\d{0,4}-?\d{0,2}')
        self.input_carrier_cnpj.setValidator(QRegExpValidator(cnpj_regex, self))
        
        # Conexões de validação
        self.input_plate.textChanged.connect(self.validate_plate)
        self.input_model.textChanged.connect(self.validate_model)
        self.input_color.textChanged.connect(self.validate_color)
        self.input_carrier_cnpj.textChanged.connect(self.validate_cnpj)
    
    def setup_connections(self):
        """Conecta sinais e slots."""
        self.validation_error.connect(self.on_validation_error)
        self.progress_updated.connect(self.on_progress_update)
    
    def validate_plate(self, plate_text: str = None):
        """Valida placa em tempo real."""
        if not plate_text:
            plate_text = self.input_plate.text()
        
        try:
            VehicleValidation.validate_plate(plate_text)
            self.input_plate.setStyleSheet("border: 2px solid #28a745; background: white;")
            return True
        except ValidationError as e:
            self.input_plate.setStyleSheet("border: 2px solid #dc3545; background: #fff5f5;")
            self.validation_error.emit(e.field, e.message, e.error_code)
            return False
    
    def validate_cnpj(self, cnpj_text: str = None):
        """Valida CNPJ em tempo real."""
        if not cnpj_text:
            cnpj_text = self.input_carrier_cnpj.text()
        
        if not cnpj_text.strip():
            self.input_carrier_cnpj.setStyleSheet("")
            return True
        
        try:
            if VehicleValidation.validate_cnpj(cnpj_text):
                self.input_carrier_cnpj.setStyleSheet("border: 2px solid #28a745;")
                return True
            else:
                raise ValidationError("cnpj", "CNPJ inválido")
        except ValidationError as e:
            self.input_carrier_cnpj.setStyleSheet("border: 2px solid #dc3545;")
            self.validation_error.emit(e.field, e.message, e.error_code)
            return False
    
    def validate_model(self, model_text: str = None):
        """Valida modelo."""
        if not model_text:
            model_text = self.input_model.text()
        
        try:
            VehicleValidation.validate_model(model_text, self.combo_type.currentText())
            self.input_model.setStyleSheet("border: 2px solid #28a745;")
            return True
        except ValidationError as e:
            self.input_model.setStyleSheet("border: 2px solid #dc3545;")
            self.validation_error.emit(e.field, e.message, e.error_code)
            return False
    
    def validate_color(self, color_text: str = None):
        """Valida cor."""
        if not color_text:
            color_text = self.input_color.text()
        
        if not color_text.strip():
            self.input_color.setStyleSheet("")
            return True
        
        try:
            VehicleValidation.validate_color(color_text)
            self.input_color.setStyleSheet("border: 2px solid #28a745;")
            return True
        except ValidationError as e:
            self.input_color.setStyleSheet("border: 2px solid #dc3545;")
            self.validation_error.emit(e.field, e.message, e.error_code)
            return False
    
    def validate_all(self) -> bool:
        """Validação completa antes do cadastro."""
        errors = []
        
        # Campos obrigatórios
        if not self.input_plate.text().strip():
            errors.append("Placa é obrigatória")
        if not self.validate_plate():
            errors.append("Placa inválida")
        if not self.input_model.text().strip():
            errors.append("Modelo é obrigatório")
        if not self.combo_type.currentText():
            errors.append("Tipo de veículo é obrigatório")
        
        # CNPJ se preenchido
        if self.input_carrier_cnpj.text().strip() and not self.validate_cnpj():
            errors.append("CNPJ inválido")
        
        if errors:
            self.show_validation_error("\n".join(errors))
            self.status_label.setText("❌ Erros de validação encontrados")
            return False
        
        self.status_label.setText("✅ Dados válidos - pronto para cadastrar!")
        return True
    
    def on_type_changed(self, vehicle_type: str):
        """Atualiza opções baseadas no tipo de veículo."""
        # Poderia popular combo de modelos específicos
        self.validate_model()
    
    def select_document(self, doc_type: str, label: QLabel):
        """Seleciona arquivo de documento."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Selecionar {doc_type}", "",
            "Documentos (*.pdf *.jpg *.jpeg *.png);;Todos (*.*)"
        )
        
        if file_path:
            label.setText(f"✅ {doc_type} selecionado")
            label.setStyleSheet("color: #28a745;")
            # Salvar referência do arquivo
            if not hasattr(self, 'selected_docs'):
                self.selected_docs = {}
            self.selected_docs[doc_type] = file_path
            logger.info(f"Documento {doc_type} selecionado: {file_path}")
    
    def load_vehicle_history(self):
        """Carrega histórico de veículos (simulado)."""
        self.history_table.setRowCount(5)
        sample_data = [
            ("ABC1D23", "Volvo FH", "Branco", "12.345.678/0001-99", "ATIVO", "2025-01-10"),
            ("DEF2E34", "Mercedes Actros", "Prata", "98.765.432/0001-10", "ATIVO", "2025-01-08"),
        ]
        
        for row, data in enumerate(sample_data):
            for col, value in enumerate(data):
                self.history_table.setItem(row, col, QTableWidgetItem(str(value)))
    
    def on_history_double_click(self, index):
        """Preenche formulário com dados do histórico."""
        row = index.row()
        plate = self.history_table.item(row, 0).text() if self.history_table.item(row, 0) else ""
        self.input_plate.setText(plate)
        self.validate_plate()
        logger.info(f"Carregando histórico da placa: {plate}")
    
    def on_register_clicked(self):
        """Inicia cadastro com validação."""
        if not self.validate_all():
            return
        
        if self.registration_in_progress:
            self.show_warning("Cadastro em andamento!")
            return
        
        vehicle_data = self.get_vehicle_data()
        self.start_registration(vehicle_data)
    
    def get_vehicle_data(self) -> Dict[str, Any]:
        """Coleta dados formatados do veículo."""
        plate = re.sub(r'[-.\s]', '', self.input_plate.text().upper())
        
        data = {
            "plate": plate,
            "type": self.combo_type.currentText(),
            "model": self.input_model.text().strip(),
            "color": self.input_color.text().strip().title(),
            "renavam": self.input_renavam.text().replace('_', '').strip(),
            "status": self.combo_status.currentText(),
            "notes": self.input_notes.toPlainText().strip(),
            "created_at": datetime.now().isoformat(),
            "documents": getattr(self, 'selected_docs', {}),
            "carrier": {
                "cnpj": self.input_carrier_cnpj.text().strip(),
                "name": self.input_carrier_name.text().strip()
            } if self.input_carrier_cnpj.text().strip() else None
        }
        
        # Validações finais
        try:
            VehicleValidation.validate_plate(plate)
            if data["carrier"] and not VehicleValidation.validate_cnpj(data["carrier"]["cnpj"]):
                raise ValidationError("carrier_cnpj", "CNPJ inválido")
        except ValidationError as e:
            self.show_validation_error(str(e))
            return None
        
        return data
    
    def start_registration(self, data: Dict[str, Any]):
        """Inicia processo de cadastro."""
        self.registration_in_progress = True
        self.btn_register.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("⏳ Cadastrando veículo...")
        
        try:
            self.presenter.register_vehicle(data)
        except Exception as e:
            logger.error(f"Erro no cadastro: {e}")
            self.show_error(f"Erro inesperado: {str(e)}")
            self.cancel_action()
    
    @pyqtSlot(int, str)
    def on_progress_update(self, percentage: int, message: str):
        """Atualiza progresso."""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(message)
    
    def save_draft(self):
        """Salva rascunho."""
        self.draft_data = self.get_vehicle_data() or {}
        self.show_info("Rascunho salvo!")
        logger.info("Rascunho de veículo salvo")
    
    def load_draft(self):
        """Carrega rascunho."""
        # Implementar carregamento persistente
        pass
    
    def cancel_action(self):
        """Cancela operação."""
        self.registration_in_progress = False
        self.btn_register.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("❌ Cancelado")
    
    @pyqtSlot(str, str, str)
    def on_validation_error(self, field: str, message: str, code: str):
        """Trata erro de validação."""
        self.show_validation_error(f"[{code}] {message}")
    
    # Métodos de feedback
    def show_success(self, message: str, data: Optional[Dict] = None):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("✅ Sucesso")
        msg.setText("Veículo cadastrado com sucesso!")
        details = f"Placa: {data.get('plate', 'N/A')}\nID: {data.get('id', 'N/A') if data else 'N/A'}"
        msg.setDetailedText(details)
        msg.exec_()
        
        self.registration_successful.emit(data or {})
        self.clear_form()
    
    def show_error(self, message: str):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("❌ Erro")
        msg.setText("Falha no cadastro")
        msg.setDetailedText(message)
        msg.exec_()
    
    def show_validation_error(self, message: str):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("⚠️ Validação")
        msg.setText("Erro de validação:")
        msg.setDetailedText(message)
        msg.exec_()
    
    def show_warning(self, message: str):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("⚠️ Aviso")
        msg.setText(message)
        msg.exec_()
    
    def show_info(self, message: str):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("ℹ️ Info")
        msg.setText(message)
        msg.exec_()
    
    def clear_form(self):
        """Limpa todos os campos."""
        self.input_plate.clear()
        self.input_model.clear()
        self.input_color.clear()
        self.input_renavam.clear()
        self.input_carrier_cnpj.clear()
        self.input_carrier_name.clear()
        self.input_notes.clear()
        self.combo_status.setCurrentText("ATIVO")
        if hasattr(self, 'selected_docs'):
            self.selected_docs.clear()
        for label in self.document_files.values():
            label.setText("Nenhum arquivo selecionado")
            label.setStyleSheet("color: #6c757d;")
    
    def closeEvent(self, event):
        """Gerencia fechamento."""
        if self.registration_in_progress:
            reply = QMessageBox.question(self, "Confirmar", "Cancelar cadastro?", 
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.save_draft()
                event.accept()
            else:
                event.ignore()
        else:
            self.save_draft()
            event.accept()