# LOGISICA/sentry/ui/views/carrier_registration_view.py

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QFormLayout,
                             QTextEdit, QGroupBox, QScrollArea)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtCore import QRegExp
from sentry.ui.presenters.carrier_registration_presenter import CarrierRegistrationPresenter
import re

class CarrierRegistrationView(QWidget):
    """
    Tela robusta para o cadastro de novas transportadoras.
    Inclui validações em tempo real e feedback visual aprimorado.
    """
    # Sinais emitidos
    registration_successful = pyqtSignal()
    validation_error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cadastrar Transportadora")
        self.setGeometry(200, 200, 500, 600)
        
        # Conecta a View ao seu Presenter
        self.presenter = CarrierRegistrationPresenter(self)
        
        # Estado de validação dos campos
        self.field_validations = {
            'name': False,
            'cnpj': False,
            'responsible_name': False,
            'contact_phone': False
        }
        
        self.setup_ui()
        self.connect_validators()

    def setup_ui(self):
        """Configura a interface do usuário."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        
        # Scroll Area para melhor visualização
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # === Informações Básicas ===
        basic_info_group = self.create_basic_info_group()
        scroll_layout.addWidget(basic_info_group)
        
        # === Informações de Contato ===
        contact_info_group = self.create_contact_info_group()
        scroll_layout.addWidget(contact_info_group)
        
        # === Informações Adicionais ===
        additional_info_group = self.create_additional_info_group()
        scroll_layout.addWidget(additional_info_group)
        
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        # === Indicador de Validação ===
        self.validation_label = QLabel()
        self.validation_label.setStyleSheet("color: #666; font-style: italic;")
        main_layout.addWidget(self.validation_label)
        
        # === Botões de Ação ===
        button_layout = self.create_button_layout()
        main_layout.addLayout(button_layout)

    def create_basic_info_group(self):
        """Cria o grupo de informações básicas."""
        group = QGroupBox("Informações Básicas")
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # Nome da Transportadora
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Ex: Transportadora Rápida Ltda")
        self.input_name.setMaxLength(100)
        self.label_name_error = QLabel()
        self.label_name_error.setStyleSheet("color: red; font-size: 10px;")
        form_layout.addRow("Nome da Transportadora: *", self.input_name)
        form_layout.addRow("", self.label_name_error)
        
        # CNPJ
        self.input_cnpj = QLineEdit()
        self.input_cnpj.setInputMask('00.000.000/0000-00;_')
        self.input_cnpj.setPlaceholderText("00.000.000/0000-00")
        self.label_cnpj_error = QLabel()
        self.label_cnpj_error.setStyleSheet("color: red; font-size: 10px;")
        form_layout.addRow("CNPJ: *", self.input_cnpj)
        form_layout.addRow("", self.label_cnpj_error)
        
        group.setLayout(form_layout)
        return group

    def create_contact_info_group(self):
        """Cria o grupo de informações de contato."""
        group = QGroupBox("Informações de Contato")
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # Nome do Responsável
        self.input_responsible_name = QLineEdit()
        self.input_responsible_name.setPlaceholderText("Ex: João Silva")
        self.input_responsible_name.setMaxLength(100)
        self.label_responsible_error = QLabel()
        self.label_responsible_error.setStyleSheet("color: red; font-size: 10px;")
        form_layout.addRow("Nome do Responsável: *", self.input_responsible_name)
        form_layout.addRow("", self.label_responsible_error)
        
        # Telefone Principal
        self.input_contact_phone = QLineEdit()
        self.input_contact_phone.setInputMask('(00) 00000-0000;_')
        self.input_contact_phone.setPlaceholderText("(00) 00000-0000")
        self.label_phone_error = QLabel()
        self.label_phone_error.setStyleSheet("color: red; font-size: 10px;")
        form_layout.addRow("Telefone Principal: *", self.input_contact_phone)
        form_layout.addRow("", self.label_phone_error)
        
        # Telefone Secundário (Opcional)
        self.input_secondary_phone = QLineEdit()
        self.input_secondary_phone.setInputMask('(00) 00000-0000;_')
        self.input_secondary_phone.setPlaceholderText("(00) 00000-0000 (Opcional)")
        form_layout.addRow("Telefone Secundário:", self.input_secondary_phone)
        
        # Email
        self.input_email = QLineEdit()
        self.input_email.setPlaceholderText("contato@transportadora.com.br")
        self.label_email_error = QLabel()
        self.label_email_error.setStyleSheet("color: red; font-size: 10px;")
        form_layout.addRow("E-mail:", self.input_email)
        form_layout.addRow("", self.label_email_error)
        
        group.setLayout(form_layout)
        return group

    def create_additional_info_group(self):
        """Cria o grupo de informações adicionais."""
        group = QGroupBox("Informações Adicionais (Opcional)")
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # Endereço
        self.input_address = QLineEdit()
        self.input_address.setPlaceholderText("Rua, número, bairro")
        form_layout.addRow("Endereço:", self.input_address)
        
        # Cidade/Estado
        city_state_layout = QHBoxLayout()
        self.input_city = QLineEdit()
        self.input_city.setPlaceholderText("Cidade")
        self.input_state = QLineEdit()
        self.input_state.setPlaceholderText("UF")
        self.input_state.setMaxLength(2)
        self.input_state.setMaximumWidth(60)
        city_state_layout.addWidget(self.input_city)
        city_state_layout.addWidget(self.input_state)
        form_layout.addRow("Cidade/Estado:", city_state_layout)
        
        # Observações
        self.input_notes = QTextEdit()
        self.input_notes.setPlaceholderText("Informações adicionais sobre a transportadora...")
        self.input_notes.setMaximumHeight(80)
        form_layout.addRow("Observações:", self.input_notes)
        
        group.setLayout(form_layout)
        return group

    def create_button_layout(self):
        """Cria o layout dos botões de ação."""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.btn_clear = QPushButton("Limpar")
        self.btn_clear.setMinimumHeight(35)
        self.btn_clear.clicked.connect(self.clear_form)
        
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setMinimumHeight(35)
        self.btn_cancel.clicked.connect(self.on_cancel_clicked)
        
        self.btn_register = QPushButton("Cadastrar")
        self.btn_register.setMinimumHeight(35)
        self.btn_register.setEnabled(False)  # Desabilitado até validação completa
        self.btn_register.clicked.connect(self.on_register_clicked)
        self.btn_register.setStyleSheet("""
            QPushButton:enabled {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        
        button_layout.addWidget(self.btn_clear)
        button_layout.addStretch()
        button_layout.addWidget(self.btn_cancel)
        button_layout.addWidget(self.btn_register)
        
        return button_layout

    def connect_validators(self):
        """Conecta os validadores aos campos."""
        self.input_name.textChanged.connect(lambda: self.validate_name())
        self.input_cnpj.textChanged.connect(lambda: self.validate_cnpj())
        self.input_responsible_name.textChanged.connect(lambda: self.validate_responsible())
        self.input_contact_phone.textChanged.connect(lambda: self.validate_phone())
        self.input_email.textChanged.connect(lambda: self.validate_email())
        self.input_state.textChanged.connect(lambda: self.input_state.setText(self.input_state.text().upper()))

    def validate_name(self):
        """Valida o nome da transportadora."""
        name = self.input_name.text().strip()
        if len(name) < 3:
            self.label_name_error.setText("Nome deve ter no mínimo 3 caracteres")
            self.field_validations['name'] = False
        elif not re.match(r'^[a-zA-ZÀ-ÿ\s\.\-&]+$', name):
            self.label_name_error.setText("Nome contém caracteres inválidos")
            self.field_validations['name'] = False
        else:
            self.label_name_error.setText("")
            self.field_validations['name'] = True
        
        self.update_register_button()

    def validate_cnpj(self):
        """Valida o CNPJ."""
        cnpj = self.input_cnpj.text().replace('.', '').replace('/', '').replace('-', '').replace('_', '')
        
        if len(cnpj) < 14:
            self.label_cnpj_error.setText("CNPJ incompleto")
            self.field_validations['cnpj'] = False
        elif not self.is_valid_cnpj(cnpj):
            self.label_cnpj_error.setText("CNPJ inválido")
            self.field_validations['cnpj'] = False
        else:
            self.label_cnpj_error.setText("")
            self.field_validations['cnpj'] = True
        
        self.update_register_button()

    def is_valid_cnpj(self, cnpj):
        """Valida o algoritmo do CNPJ."""
        if not cnpj.isdigit() or len(cnpj) != 14:
            return False
        
        # Verifica CNPJs conhecidos como inválidos
        if cnpj == cnpj[0] * 14:
            return False
        
        # Calcula o primeiro dígito verificador
        sum_1 = sum(int(cnpj[i]) * (5 - i if i < 4 else 13 - i) for i in range(12))
        digit_1 = 11 - (sum_1 % 11)
        digit_1 = 0 if digit_1 >= 10 else digit_1
        
        if int(cnpj[12]) != digit_1:
            return False
        
        # Calcula o segundo dígito verificador
        sum_2 = sum(int(cnpj[i]) * (6 - i if i < 5 else 14 - i) for i in range(13))
        digit_2 = 11 - (sum_2 % 11)
        digit_2 = 0 if digit_2 >= 10 else digit_2
        
        return int(cnpj[13]) == digit_2

    def validate_responsible(self):
        """Valida o nome do responsável."""
        name = self.input_responsible_name.text().strip()
        if len(name) < 3:
            self.label_responsible_error.setText("Nome deve ter no mínimo 3 caracteres")
            self.field_validations['responsible_name'] = False
        elif not re.match(r'^[a-zA-ZÀ-ÿ\s]+$', name):
            self.label_responsible_error.setText("Nome contém caracteres inválidos")
            self.field_validations['responsible_name'] = False
        else:
            self.label_responsible_error.setText("")
            self.field_validations['responsible_name'] = True
        
        self.update_register_button()

    def validate_phone(self):
        """Valida o telefone."""
        phone = self.input_contact_phone.text().replace('(', '').replace(')', '').replace(' ', '').replace('-', '').replace('_', '')
        
        if len(phone) < 10:
            self.label_phone_error.setText("Telefone incompleto")
            self.field_validations['contact_phone'] = False
        elif phone.startswith('00') or phone[2:4] == '00':
            self.label_phone_error.setText("DDD ou número inválido")
            self.field_validations['contact_phone'] = False
        else:
            self.label_phone_error.setText("")
            self.field_validations['contact_phone'] = True
        
        self.update_register_button()

    def validate_email(self):
        """Valida o e-mail (campo opcional)."""
        email = self.input_email.text().strip()
        if email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            self.label_email_error.setText("E-mail inválido")
        else:
            self.label_email_error.setText("")

    def update_register_button(self):
        """Atualiza o estado do botão de cadastro baseado nas validações."""
        all_valid = all(self.field_validations.values())
        self.btn_register.setEnabled(all_valid)
        
        if all_valid:
            self.validation_label.setText("✓ Todos os campos obrigatórios estão válidos")
            self.validation_label.setStyleSheet("color: green; font-style: italic;")
        else:
            invalid_count = sum(1 for v in self.field_validations.values() if not v)
            self.validation_label.setText(f"⚠ {invalid_count} campo(s) obrigatório(s) pendente(s)")
            self.validation_label.setStyleSheet("color: orange; font-style: italic;")

    def on_register_clicked(self):
        """Coleta os dados validados e envia para o Presenter."""
        # Confirmação antes de cadastrar
        reply = QMessageBox.question(
            self, 
            'Confirmar Cadastro',
            f'Deseja cadastrar a transportadora "{self.input_name.text()}"?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
        
        # Desabilita o botão durante o processamento
        self.btn_register.setEnabled(False)
        self.btn_register.setText("Cadastrando...")
        
        carrier_data = {
            "name": self.input_name.text().strip(),
            "cnpj": self.input_cnpj.text(),
            "responsible_name": self.input_responsible_name.text().strip(),
            "contact_phone": self.input_contact_phone.text(),
            "secondary_phone": self.input_secondary_phone.text() if self.input_secondary_phone.text().replace('(', '').replace(')', '').replace(' ', '').replace('-', '').replace('_', '') else None,
            "email": self.input_email.text().strip() if self.input_email.text().strip() else None,
            "address": self.input_address.text().strip() if self.input_address.text().strip() else None,
            "city": self.input_city.text().strip() if self.input_city.text().strip() else None,
            "state": self.input_state.text().strip().upper() if self.input_state.text().strip() else None,
            "notes": self.input_notes.toPlainText().strip() if self.input_notes.toPlainText().strip() else None
        }
        
        self.presenter.register_carrier(carrier_data)

    def on_cancel_clicked(self):
        """Confirma o cancelamento se houver dados preenchidos."""
        has_data = any([
            self.input_name.text().strip(),
            self.input_cnpj.text().replace('.', '').replace('/', '').replace('-', '').replace('_', ''),
            self.input_responsible_name.text().strip(),
            self.input_contact_phone.text().replace('(', '').replace(')', '').replace(' ', '').replace('-', '').replace('_', '')
        ])
        
        if has_data:
            reply = QMessageBox.question(
                self,
                'Confirmar Cancelamento',
                'Existem dados não salvos. Deseja realmente cancelar?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.close()
        else:
            self.close()

    # === Métodos chamados pelo Presenter para atualizar a UI ===
    
    def show_success(self, message):
        """Exibe mensagem de sucesso."""
        QMessageBox.information(self, "Sucesso", message)
        self.registration_successful.emit()
        self.close()

    def show_error(self, message):
        """Exibe mensagem de erro."""
        QMessageBox.critical(self, "Erro de Cadastro", message)
        # Reabilita o botão de cadastro
        self.btn_register.setEnabled(True)
        self.btn_register.setText("Cadastrar")

    def show_warning(self, message):
        """Exibe mensagem de aviso."""
        QMessageBox.warning(self, "Aviso", message)

    def clear_form(self):
        """Limpa todos os campos do formulário."""
        reply = QMessageBox.question(
            self,
            'Limpar Formulário',
            'Deseja realmente limpar todos os campos?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.input_name.clear()
            self.input_cnpj.clear()
            self.input_responsible_name.clear()
            self.input_contact_phone.clear()
            self.input_secondary_phone.clear()
            self.input_email.clear()
            self.input_address.clear()
            self.input_city.clear()
            self.input_state.clear()
            self.input_notes.clear()
            
            # Limpa os labels de erro
            self.label_name_error.setText("")
            self.label_cnpj_error.setText("")
            self.label_responsible_error.setText("")
            self.label_phone_error.setText("")
            self.label_email_error.setText("")
            
            # Reseta as validações
            for key in self.field_validations:
                self.field_validations[key] = False
            self.update_register_button()
            
            # Foca no primeiro campo
            self.input_name.setFocus()

    def set_loading_state(self, is_loading):
        """Define o estado de carregamento da interface."""
        self.btn_register.setEnabled(not is_loading)
        self.btn_cancel.setEnabled(not is_loading)
        self.btn_clear.setEnabled(not is_loading)
        
        if is_loading:
            self.btn_register.setText("Cadastrando...")
        else:
            self.btn_register.setText("Cadastrar")