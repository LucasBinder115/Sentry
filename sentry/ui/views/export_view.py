# LOGISICA/sentry/ui/views/export_view.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QPushButton, 
    QMessageBox, QComboBox, QDateEdit, QGroupBox, QProgressBar, QSpinBox,
    QCheckBox, QTextEdit, QSplitter, QSizePolicy
)
from PyQt5.QtCore import QDate, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sentry.ui.presenters.export_presenter import ExportPresenter
import logging

logger = logging.getLogger(__name__)

class ExportView(QWidget):
    """
    Tela avançada para exportar registros de acesso com validações, progresso e configurações avançadas.
    """
    
    # Sinais para comunicação com presenter
    export_completed = pyqtSignal(str, bool)  # filename, success
    progress_updated = pyqtSignal(int)  # progress percentage
    validation_error = pyqtSignal(str)  # error message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exportar Registros - Sistema LOGISICA")
        self.setGeometry(200, 200, 600, 500)
        self.setMinimumSize(500, 400)
        
        # Configurações iniciais
        self.presenter = ExportPresenter(self)
        self.export_in_progress = False
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_progress)
        
        self.setup_ui()
        self.connect_signals()
        self.setup_validations()
        
    def setup_ui(self):
        """Configura a interface com layout melhorado e componentes avançados."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Título
        title_label = QLabel("Exportação de Registros de Acesso")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Splitter para separar configurações e preview
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(5)
        
        # Configurações principais
        config_widget = self.setup_config_panel()
        preview_widget = self.setup_preview_panel()
        
        splitter.addWidget(config_widget)
        splitter.addWidget(preview_widget)
        splitter.setSizes([400, 150])
        
        main_layout.addWidget(splitter)
        
        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        main_layout.addWidget(self.progress_bar)
        
        # Botões de ação
        self.setup_action_buttons(main_layout)
        
        # Status bar
        self.status_label = QLabel("Pronto para exportar")
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        main_layout.addWidget(self.status_label)
        
    def setup_config_panel(self) -> QWidget:
        """Configura o painel principal de configurações."""
        config_group = QGroupBox("Configurações de Exportação")
        config_layout = QFormLayout(config_group)
        config_layout.setLabelAlignment(Qt.AlignRight)
        config_layout.setFormAlignment(Qt.AlignLeft)
        
        # Formato de arquivo
        self.combo_file_type = QComboBox()
        self.combo_file_type.addItems(["CSV", "PDF", "Excel", "JSON"])
        self.combo_file_type.currentTextChanged.connect(self.on_file_type_changed)
        config_layout.addRow("Formato:", self.combo_file_type)
        
        # Período de datas com validação
        date_layout = QHBoxLayout()
        self.date_start = QDateEdit(calendarPopup=True)
        self.date_start.setDate(QDate.currentDate().addMonths(-1))
        self.date_start.setMaximumDate(QDate.currentDate())
        self.date_start.dateChanged.connect(self.validate_dates)
        
        self.date_end = QDateEdit(calendarPopup=True)
        self.date_end.setDate(QDate.currentDate())
        self.date_end.setMinimumDate(self.date_start.date())
        self.date_end.dateChanged.connect(self.validate_dates)
        
        date_layout.addWidget(self.date_start)
        date_layout.addWidget(QLabel("até"))
        date_layout.addWidget(self.date_end)
        config_layout.addRow("Período:", date_layout)
        
        # Filtros avançados
        advanced_group = QGroupBox("Filtros Avançados")
        advanced_layout = QVBoxLayout(advanced_group)
        
        filter_layout = QHBoxLayout()
        self.check_active_only = QCheckBox("Apenas registros ativos")
        self.check_active_only.setChecked(True)
        filter_layout.addWidget(self.check_active_only)
        
        self.check_include_metadata = QCheckBox("Incluir metadados completos")
        filter_layout.addWidget(self.check_include_metadata)
        advanced_layout.addLayout(filter_layout)
        
        # Limite de registros
        limit_layout = QHBoxLayout()
        limit_layout.addWidget(QLabel("Máximo de registros:"))
        self.spin_limit = QSpinBox()
        self.spin_limit.setRange(100, 1000000)
        self.spin_limit.setValue(10000)
        self.spin_limit.setSuffix(" registros")
        limit_layout.addWidget(self.spin_limit)
        advanced_layout.addLayout(limit_layout)
        
        config_layout.addRow(advanced_group)
        
        # Diretório de saída
        self.edit_output_dir = QTextEdit()
        self.edit_output_dir.setMaximumHeight(60)
        self.edit_output_dir.setPlaceholderText("Diretório de saída será definido automaticamente...")
        self.edit_output_dir.setReadOnly(True)
        config_layout.addRow("Diretório de saída:", self.edit_output_dir)
        
        return config_group
    
    def setup_preview_panel(self) -> QWidget:
        """Configura o painel de preview e log."""
        preview_group = QGroupBox("Pré-visualização e Log")
        preview_layout = QVBoxLayout(preview_group)
        
        # Preview de campos
        self.preview_label = QLabel("Selecione as configurações para ver preview dos campos exportados")
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("padding: 10px; color: #666;")
        preview_layout.addWidget(self.preview_label)
        
        # Log area
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(100)
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("Log de atividades será exibido aqui...")
        preview_layout.addWidget(self.log_text)
        
        return preview_group
    
    def setup_action_buttons(self, parent_layout: QVBoxLayout):
        """Configura os botões de ação."""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        # Botão validar
        self.btn_validate = QPushButton("Validar Configurações")
        self.btn_validate.clicked.connect(self.validate_configuration)
        self.btn_validate.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; }")
        button_layout.addWidget(self.btn_validate)
        
        # Botão exportar
        self.btn_export = QPushButton("🚀 Iniciar Exportação")
        self.btn_export.clicked.connect(self.on_export_clicked)
        self.btn_export.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; }")
        self.btn_export.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        button_layout.addWidget(self.btn_export)
        
        # Botão cancelar
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.cancel_export)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setStyleSheet("QPushButton { background-color: #f44336; color: white; }")
        button_layout.addWidget(self.btn_cancel)
        
        parent_layout.addLayout(button_layout)
    
    def connect_signals(self):
        """Conecta sinais do presenter com a view."""
        self.export_completed.connect(self.on_export_completed)
        self.progress_updated.connect(self.progress_bar.setValue)
        self.validation_error.connect(self.show_validation_error)
        
        # Conexões do presenter
        if hasattr(self.presenter, 'export_completed'):
            self.presenter.export_completed.connect(self.export_completed)
        if hasattr(self.presenter, 'progress_updated'):
            self.presenter.progress_updated.connect(self.progress_updated)
    
    def setup_validations(self):
        """Configura validações automáticas."""
        self.date_start.dateChanged.connect(self.validate_dates)
        self.date_end.dateChanged.connect(self.validate_dates)
        self.combo_file_type.currentTextChanged.connect(self.on_file_type_changed)
    
    def validate_dates(self):
        """Valida se as datas estão em ordem cronológica."""
        start_date = self.date_start.date()
        end_date = self.date_end.date()
        
        if start_date > end_date:
            self.date_end.setDate(start_date)
            self.show_warning("Data final ajustada para ser posterior à data inicial.")
        
        # Limita período máximo (ex: 1 ano)
        max_period = timedelta(days=365)
        if (end_date.toPyDate() - start_date.toPyDate()) > max_period:
            self.show_warning("Período máximo de 1 ano. Ajustando data final.")
            self.date_end.setDate(start_date.addDays(365))
    
    def validate_configuration(self):
        """Valida toda a configuração antes da exportação."""
        errors = []
        
        # Validação de datas
        start_date = self.date_start.date()
        end_date = self.date_end.date()
        if start_date > end_date:
            errors.append("Data inicial deve ser anterior à data final.")
        
        # Validação de limite
        if self.spin_limit.value() < 100:
            errors.append("Mínimo de 100 registros por exportação.")
        
        if errors:
            self.show_validation_error("\n".join(errors))
            return False
        
        self.log_message("✅ Configuração validada com sucesso!")
        self.show_info("Configuração válida. Pronto para exportar!")
        return True
    
    def on_file_type_changed(self, file_type: str):
        """Atualiza preview baseado no tipo de arquivo."""
        supported_fields = {
            "CSV": ["id", "data", "usuario", "acesso", "status"],
            "PDF": ["id", "data", "usuario", "acesso"],
            "Excel": ["id", "data", "usuario", "acesso", "status", "metadata"],
            "JSON": ["id", "data", "usuario", "acesso", "status", "metadata", "raw"]
        }
        
        fields = supported_fields.get(file_type, ["id", "data", "usuario"])
        preview_text = f"Campos exportados ({file_type}): {', '.join(fields)}"
        self.preview_label.setText(preview_text)
    
    def on_export_clicked(self):
        """Inicia processo de exportação com validações."""
        if not self.validate_configuration():
            return
            
        if self.export_in_progress:
            self.show_warning("Exportação já em andamento!")
            return
        
        export_params = self.get_export_params()
        self.start_export(export_params)
    
    def get_export_params(self) -> Dict[str, Any]:
        """Retorna parâmetros de exportação formatados."""
        return {
            "file_type": self.combo_file_type.currentText().lower(),
            "date_start": self.date_start.date().toString("yyyy-MM-dd"),
            "date_end": self.date_end.date().toString("yyyy-MM-dd"),
            "limit": self.spin_limit.value(),
            "active_only": self.check_active_only.isChecked(),
            "include_metadata": self.check_include_metadata.isChecked(),
            "output_dir": self.get_output_directory()
        }
    
    def start_export(self, params: Dict[str, Any]):
        """Inicia exportação com UI feedback."""
        self.export_in_progress = True
        self.btn_export.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Iniciando exportação...")
        
        self.log_message(f"🚀 Iniciando exportação: {params['file_type']} de {params['date_start']} até {params['date_end']}")
        
        try:
            self.presenter.export_records(params)
        except Exception as e:
            logger.error(f"Erro ao iniciar exportação: {str(e)}")
            self.show_error(f"Erro inesperado: {str(e)}")
            self.cancel_export()
    
    def update_progress(self):
        """Atualiza progresso da exportação."""
        # Esta função pode ser chamada periodicamente durante exportações longas
        current_value = self.progress_bar.value()
        if current_value < 90:  # Simula progresso
            self.progress_bar.setValue(current_value + 5)
    
    def cancel_export(self):
        """Cancela exportação em andamento."""
        if self.export_in_progress:
            self.presenter.cancel_export()
            self.export_in_progress = False
            self.btn_export.setEnabled(True)
            self.btn_cancel.setEnabled(False)
            self.progress_bar.setVisible(False)
            self.status_label.setText("Exportação cancelada")
            self.log_message("❌ Exportação cancelada pelo usuário")
    
    def on_export_completed(self, filename: str, success: bool):
        """Callback de conclusão da exportação."""
        self.export_in_progress = False
        self.progress_bar.setVisible(False)
        self.btn_export.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        
        if success:
            self.status_label.setText("Exportação concluída com sucesso!")
            self.show_success(f"Arquivo exportado: {filename}")
            self.log_message(f"✅ Exportação concluída: {filename}")
        else:
            self.status_label.setText("Exportação falhou")
            self.show_error("Falha na exportação. Verifique os logs.")
            self.log_message("❌ Exportação falhou")
    
    def get_output_directory(self) -> str:
        """Retorna diretório de saída padrão."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"/exports/registros_{timestamp}"
    
    def log_message(self, message: str):
        """Adiciona mensagem ao log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.append(log_entry)
        logger.info(message)
    
    # Métodos de feedback melhorados
    def show_success(self, message: str):
        """Exibe mensagem de sucesso com ícone."""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("Sucesso")
        msg_box.setText("✅ Operação realizada com sucesso!")
        msg_box.setDetailedText(message)
        msg_box.exec_()
    
    def show_error(self, message: str):
        """Exibe erro com detalhes."""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Erro")
        msg_box.setText("❌ Erro na operação")
        msg_box.setDetailedText(message)
        msg_box.exec_()
    
    def show_warning(self, message: str):
        """Exibe aviso."""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Aviso")
        msg_box.setText(f"⚠️ {message}")
        msg_box.exec_()
    
    def show_info(self, message: str):
        """Exibe informação."""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle("Informação")
        msg_box.setText(f"ℹ️ {message}")
        msg_box.exec_()
    
    def show_validation_error(self, message: str):
        """Exibe erro de validação."""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Validação")
        msg_box.setText("❌ Erro de validação:")
        msg_box.setDetailedText(message)
        msg_box.exec_()
    
    def closeEvent(self, event):
        """Limpa recursos ao fechar."""
        if self.export_in_progress:
            reply = QMessageBox.question(
                self, "Confirmar", 
                "Exportação em andamento. Deseja cancelar?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.cancel_export()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()