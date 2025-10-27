# LOGISICA/sentry/ui/views/login.py

from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, 
    QFrame, QMessageBox, QProgressBar, QCheckBox, QSpacerItem, 
    QSizePolicy, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QRegExp, QPropertyAnimation, QEasingCurve, QTimer, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QPixmap, QRegExpValidator, QIcon, QPalette
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import json
import os

logger = logging.getLogger(__name__)

# =========================================================
# CAMADA CORE/DOMAIN - MELHORADA E ROBUSTA
# =========================================================

class AuthError(Exception):
    """Classe base para erros de autenticação com códigos de erro."""
    def __init__(self, message: str, error_code: str = "AUTH_000"):
        self.message = message
        self.error_code = error_code
        super().__init__(message)

class UserNotFoundError(AuthError):
    def __init__(self, message: str = "Usuário não encontrado"):
        super().__init__(message, "AUTH_001")

class InvalidCredentialsError(AuthError):
    def __init__(self, message: str = "Credenciais inválidas"):
        super().__init__(message, "AUTH_002")

class AccountLockedError(AuthError):
    def __init__(self, message: str = "Conta bloqueada temporariamente"):
        super().__init__(message, "AUTH_003")

class MaxLoginAttemptsError(AuthError):
    def __init__(self, message: str = "Muitas tentativas. Conta bloqueada"):
        super().__init__(message, "AUTH_004")

class DatabaseConnectionError(AuthError):
    def __init__(self, message: str = "Erro de conexão com banco de dados"):
        super().__init__(message, "INFRA_001")

class SessionManager:
    """Gerencia sessões de usuário com tokens JWT simulados."""
    
    @staticmethod
    def generate_token(username: str, duration_minutes: int = 30) -> str:
        """Gera token de sessão seguro."""
        payload = {
            "username": username,
            "exp": datetime.now().timestamp() + (duration_minutes * 60),
            "iat": datetime.now().timestamp()
        }
        # Em produção, usaria JWT real
        token = hashlib.sha256(json.dumps(payload).encode()).hexdigest()
        return token
    
    @staticmethod
    def validate_token(token: str, username: str) -> bool:
        """Valida token de sessão."""
        try:
            # Simulação de validação JWT
            return len(token) == 64 and username
        except:
            return False

class SecurityUtils:
    """Utilitários de segurança para autenticação."""
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Hash seguro de senha com salt."""
        if salt is None:
            salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return salt, hashed.hex()
    
    @staticmethod
    def verify_password(password: str, salt: str, stored_hash: str) -> bool:
        """Verifica senha contra hash armazenado."""
        _, hashed = SecurityUtils.hash_password(password, salt)
        return hashed == stored_hash

class UserRepository:
    """Repositório de usuários com cache e tentativas de login."""
    
    def __init__(self, db_path: str = "sentry.db"):
        self.db_path = db_path
        self._cache = {}
        self._login_attempts = {}  # {username: {"count": int, "last_attempt": datetime, "locked_until": datetime}}
        self._load_users()
    
    def _load_users(self):
        """Carrega usuários do "banco" com hashes seguros."""
        # USUÁRIOS DE DEMONSTRAÇÃO - SENHA FÁCIL PARA TESTES
        # Senha padrão para todos: 123456
        demo_password = "123456"
        
        # Gera hash para a senha de demonstração
        salt_demo, hash_demo = SecurityUtils.hash_password(demo_password)
        
        self._users = {
            "LUCAS": {
                "salt": salt_demo,
                "password_hash": hash_demo,
                "nome_completo": "Lucas Binder",
                "role": "admin",
                "last_login": None,
                "is_active": True,
                "email": "lucas@logisica.com"
            },
            "ADMIN": {
                "salt": salt_demo,
                "password_hash": hash_demo,
                "nome_completo": "Administrador Sistema",
                "role": "superadmin",
                "last_login": None,
                "is_active": True,
                "email": "admin@logisica.com"
            },
            "OPERADOR": {
                "salt": salt_demo,
                "password_hash": hash_demo,
                "nome_completo": "Operador Portaria",
                "role": "operator",
                "last_login": None,
                "is_active": True,
                "email": "operador@logisica.com"
            },
            "TESTE": {
                "salt": salt_demo,
                "password_hash": hash_demo,
                "nome_completo": "Usuário de Testes",
                "role": "viewer",
                "last_login": None,
                "is_active": True,
                "email": "teste@logisica.com"
            }
        }
        
        logger.info("Repositório de usuários inicializado com usuários de demonstração")
        logger.info(f"Usuários disponíveis: {list(self._users.keys())}")
        logger.info("Senha padrão para todos: 123456")
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Busca usuário com validação de cache e bloqueio."""
        username = username.upper().strip()  # Agora é case-insensitive para maiúsculas
        
        # Verifica tentativas de login
        if self._is_account_locked(username):
            raise AccountLockedError("Conta bloqueada por tentativas excessivas")
        
        user = self._users.get(username)
        if not user:
            self._increment_login_attempt(username)
            raise UserNotFoundError("Usuário não encontrado")
        
        if not user.get("is_active", True):
            raise InvalidCredentialsError("Conta desativada")
        
        return user
    
    def _is_account_locked(self, username: str) -> bool:
        """Verifica se conta está bloqueada."""
        attempts = self._login_attempts.get(username, {})
        locked_until = attempts.get("locked_until")
        if locked_until and datetime.now() < locked_until:
            return True
        return False
    
    def _increment_login_attempt(self, username: str):
        """Incrementa contador de tentativas."""
        now = datetime.now()
        attempts = self._login_attempts.setdefault(username, {"count": 0, "last_attempt": now})
        
        attempts["count"] += 1
        attempts["last_attempt"] = now
        
        # Bloqueia após 5 tentativas por 15 minutos
        if attempts["count"] >= 5:
            attempts["locked_until"] = now + timedelta(minutes=15)
            raise MaxLoginAttemptsError("Conta bloqueada temporariamente")
    
    def update_last_login(self, username: str):
        """Atualiza última data de login."""
        if username in self._users:
            self._users[username]["last_login"] = datetime.now()
            logger.info(f"Login atualizado para usuário: {username}")
    
    def clear_login_attempts(self, username: str):
        """Limpa tentativas após login bem-sucedido."""
        self._login_attempts.pop(username, None)
        logger.info(f"Tentativas de login limpas para: {username}")

class AuthUseCase:
    """Caso de uso principal de autenticação com segurança."""
    
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION = timedelta(minutes=15)
    
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
        self.session_manager = SessionManager()
    
    def authenticate(self, username: str, password: str, remember_me: bool = False) -> Dict[str, Any]:
        """Autentica usuário com verificações de segurança."""
        try:
            # Normaliza username para maiúsculas
            username = username.upper().strip()
            
            logger.info(f"Tentativa de login para: {username}")
            
            # Busca usuário
            user_data = self.user_repo.get_user_by_username(username)
            
            # Verifica senha
            salt = user_data["salt"]
            password_hash = user_data["password_hash"]
            
            if not SecurityUtils.verify_password(password, salt, password_hash):
                self.user_repo._increment_login_attempt(username)
                raise InvalidCredentialsError("Senha incorreta")
            
            # Login bem-sucedido
            self.user_repo.clear_login_attempts(username)
            self.user_repo.update_last_login(username)
            
            # Gera token de sessão
            duration = 1440 if remember_me else 30  # 24h vs 30min
            token = self.session_manager.generate_token(username, duration)
            
            logger.info(f"Login bem-sucedido para: {username}")
            
            return {
                "username": username,
                "nome_completo": user_data["nome_completo"],
                "role": user_data["role"],
                "token": token,
                "last_login": user_data["last_login"],
                "remember_me": remember_me,
                "email": user_data.get("email", ""),
                "login_time": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            }
            
        except AuthError:
            raise  # Re-raise erros de autenticação
        except Exception as e:
            logger.error(f"Erro inesperado na autenticação: {e}")
            raise DatabaseConnectionError("Erro interno do sistema")

# =========================================================
# WORKER ASSÍNCRONO PARA LOGIN
# =========================================================

class AuthWorker(QThread):
    """Worker assíncrono para autenticação sem bloquear UI."""
    
    login_success = pyqtSignal(dict)
    login_error = pyqtSignal(str, str)  # message, error_code
    login_progress = pyqtSignal(str)
    
    def __init__(self, auth_usecase: AuthUseCase, username: str, password: str, remember_me: bool):
        super().__init__()
        self.auth_usecase = auth_usecase
        self.username = username
        self.password = password
        self.remember_me = remember_me
    
    @pyqtSlot()
    def run(self):
        """Executa autenticação em thread separada."""
        try:
            self.login_progress.emit("Validando credenciais...")
            user_data = self.auth_usecase.authenticate(self.username, self.password, self.remember_me)
            self.login_success.emit(user_data)
        except AuthError as e:
            self.login_error.emit(str(e), e.error_code)
        except Exception as e:
            self.login_error.emit("Erro interno do sistema", "AUTH_999")

# =========================================================
# INTERFACE AVANÇADA E ROBUSTA
# =========================================================

class LoginPage(QWidget):
    """Página de login robusta com animações, segurança e UX avançada."""
    
    login_successful = pyqtSignal(dict)
    show_progress = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(450, 400)
        self.setWindowTitle("SENTRY.INC - Autenticação Segura")
        
        # Inicialização da lógica
        self.user_repo = UserRepository()
        self.auth_usecase = AuthUseCase(self.user_repo)
        self.current_worker = None
        
        self.init_ui()
        self.setup_validators()
        self.setup_animations()
        
        # Salva preferências
        self.load_preferences()
    
    def init_ui(self):
        """Interface moderna com animações e feedback visual."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)
        
        # Header com logo/branding
        header_layout = QHBoxLayout()
        header_layout.addStretch()
        
        title_label = QLabel("🔒 SENTRY.INC")
        title_font = QFont("Segoe UI", 20, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2c3e50; margin: 10px;")
        header_layout.addWidget(title_label, alignment=Qt.AlignCenter)
        
        subtitle_label = QLabel("Sistema de Controle de Acesso")
        subtitle_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        header_layout.addWidget(subtitle_label, alignment=Qt.AlignCenter)
        
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        # Form container com sombra/elevação
        form_frame = QFrame()
        form_frame.setObjectName("formFrame")
        form_frame.setStyleSheet("""
            #formFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #ffffff, stop:1 #f8f9fa);
                border-radius: 12px;
                border: 1px solid #e9ecef;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
        """)
        
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(30, 30, 30, 30)
        form_layout.setSpacing(20)
        
        # Campos de entrada com ícones
        self.create_input_field(form_layout, "👤 Usuário", "Digite LUCAS para demo", "user_entry")
        self.create_input_field(form_layout, "🔑 Senha", "Digite 123456 para demo", "pass_entry", password=True)
        
        # Informações de demonstração
        demo_info = QLabel("💡 Demo: Use LUCAS / 123456")
        demo_info.setStyleSheet("""
            QLabel {
                background: #e3f2fd;
                border: 1px solid #bbdefb;
                border-radius: 6px;
                padding: 8px;
                color: #1976d2;
                font-size: 12px;
                text-align: center;
            }
        """)
        form_layout.addWidget(demo_info)
        
        # Opções avançadas
        options_layout = QHBoxLayout()
        self.remember_me = QCheckBox("Lembrar por 24h")
        self.remember_me.setStyleSheet("QCheckBox { color: #6c757d; spacing: 8px; }")
        options_layout.addWidget(self.remember_me)
        
        options_layout.addStretch()
        self.show_attempts = QLabel("")  # Mostra tentativas restantes
        self.show_attempts.setStyleSheet("color: #6c757d; font-size: 11px;")
        options_layout.addWidget(self.show_attempts)
        form_layout.addLayout(options_layout)
        
        # Botões
        button_layout = QHBoxLayout()
        self.login_btn = QPushButton("🚀 Entrar")
        self.login_btn.setObjectName("loginBtn")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self.attempt_login)
        self.login_btn.setStyleSheet("""
            #loginBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #007bff, stop:1 #0056b3);
                color: white; 
                font-weight: bold; 
                border-radius: 6px; 
                padding: 12px;
                border: none;
            }
            #loginBtn:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0056b3, stop:1 #004085); }
            #loginBtn:pressed { background: #004085; }
            #loginBtn:disabled { background: #6c757d; }
        """)
        
        self.forgot_btn = QPushButton("Esqueceu a senha?")
        self.forgot_btn.setStyleSheet("""
            QPushButton { 
                color: #007bff; 
                background: transparent; 
                border: none; 
                text-decoration: underline;
                padding: 8px;
            }
            QPushButton:hover { color: #0056b3; }
        """)
        self.forgot_btn.clicked.connect(self.show_forgot_password)
        
        button_layout.addWidget(self.login_btn)
        button_layout.addWidget(self.forgot_btn)
        form_layout.addLayout(button_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        form_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(form_frame, alignment=Qt.AlignCenter)
        main_layout.addStretch()
        
        # Foco inicial
        QTimer.singleShot(100, lambda: self.user_entry.setFocus())
        
        self.user_entry.returnPressed.connect(lambda: self.pass_entry.setFocus())
        self.pass_entry.returnPressed.connect(self.attempt_login)
    
    def create_input_field(self, parent_layout, label_text: str, placeholder: str, 
                          target_widget_name: str, password: bool = False):
        """Cria campo de entrada estilizado."""
        field_layout = QHBoxLayout()
        
        label = QLabel(label_text)
        label.setStyleSheet("QLabel { color: #495057; font-weight: 500; min-width: 80px; }")
        field_layout.addWidget(label)
        
        widget = QLineEdit()
        widget.setPlaceholderText(placeholder)
        widget.setObjectName("inputField")
        
        if password:
            widget.setEchoMode(QLineEdit.Password)
            # Toggle visibilidade senha
            toggle_btn = QPushButton("👁")
            toggle_btn.setFixedSize(30, 30)
            toggle_btn.setStyleSheet("""
                QPushButton {
                    background: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background: #e9ecef;
                }
            """)
            toggle_btn.clicked.connect(lambda: self.toggle_password_visibility(widget, toggle_btn))
            field_layout.addWidget(toggle_btn)
        
        widget.setStyleSheet("""
            QLineEdit#inputField {
                padding: 12px; 
                border: 2px solid #e9ecef; 
                border-radius: 6px; 
                background: white;
                font-size: 14px;
            }
            QLineEdit#inputField:focus {
                border: 2px solid #007bff; 
                background: #f8f9ff;
            }
            QLineEdit#inputField:!focus:placeholder {
                color: #adb5bd;
            }
        """)
        
        field_layout.addWidget(widget)
        parent_layout.addLayout(field_layout)
        
        # Atribuir o widget ao objeto usando o nome fornecido
        setattr(self, target_widget_name, widget)
    
    def toggle_password_visibility(self, line_edit: QLineEdit, button: QPushButton):
        """Alterna visibilidade da senha."""
        if line_edit.echoMode() == QLineEdit.Password:
            line_edit.setEchoMode(QLineEdit.Normal)
            button.setText("🔒")
        else:
            line_edit.setEchoMode(QLineEdit.Password)
            button.setText("👁")
    
    def setup_validators(self):
        """Configura validadores avançados."""
        # Username: letras, números, underscores (máx 20 chars)
        user_regex = QRegExp("^[a-zA-Z0-9_]{3,20}$")
        self.user_entry.setValidator(QRegExpValidator(user_regex))
        
        # Senha: mínimo 6 caracteres
        self.pass_entry.textChanged.connect(self.validate_password_strength)
    
    def validate_password_strength(self):
        """Valida força da senha em tempo real."""
        password = self.pass_entry.text()
        strength = "fraca" if len(password) < 6 else "boa" if len(password) < 12 else "forte"
        # Poderia adicionar indicador visual de força
        logger.debug(f"Força da senha: {strength}")
    
    def setup_animations(self):
        """Configura animações para feedback visual."""
        self.login_animation = QPropertyAnimation(self.login_btn, b"geometry")
        self.login_animation.setDuration(200)
        self.login_animation.setEasingCurve(QEasingCurve.InOutQuad)
    
    def attempt_login(self):
        """Inicia processo de login assíncrono."""
        username = self.user_entry.text().strip()
        password = self.pass_entry.text().strip()
        
        # Validações de UI
        if not self._validate_inputs(username, password):
            return
        
        # Desabilita UI e mostra progresso
        self._set_ui_state(logging=True)
        self.show_progress.emit(True)
        
        # Cria worker assíncrono
        self.current_worker = AuthWorker(
            self.auth_usecase, username, password, self.remember_me.isChecked()
        )
        self.current_worker.login_success.connect(self._on_login_success)
        self.current_worker.login_error.connect(self._on_login_error)
        self.current_worker.login_progress.connect(self._on_login_progress)
        self.current_worker.finished.connect(self._on_worker_finished)
        
        self.current_worker.start()
    
    def _validate_inputs(self, username: str, password: str) -> bool:
        """Valida entradas do usuário."""
        if not username:
            self._show_error("Por favor, digite seu nome de usuário.", self.user_entry)
            return False
        
        if self.user_entry.validator():
            state = self.user_entry.validator().validate(username, 0)[0]
            if state != QRegExpValidator.Acceptable:
                self._show_error("Usuário deve ter 3-20 caracteres (letras, números, _)", self.user_entry)
                return False
        
        if len(password) < 6:
            self._show_error("Senha deve ter pelo menos 6 caracteres", self.pass_entry)
            return False
        
        return True
    
    def _set_ui_state(self, logging: bool):
        """Gerencia estado da UI durante login."""
        self.login_btn.setEnabled(not logging)
        self.progress_bar.setVisible(logging)
        if logging:
            self.login_btn.setText("Entrando...")
        else:
            self.login_btn.setText("🚀 Entrar")
    
    @pyqtSlot(dict)
    def _on_login_success(self, user_data: dict):
        """Callback de login bem-sucedido."""
        logger.info(f"Login bem-sucedido para {user_data['username']}")
        
        # Salva preferências
        self.save_preferences(user_data['username'], self.remember_me.isChecked())
        
        # Emite sinal para aplicação principal
        self.login_successful.emit(user_data)
        
        self._show_success(f"Bem-vindo, {user_data['nome_completo']}! 🎉\n\nAcessando dashboard...")
        self._set_ui_state(logging=False)
    
    @pyqtSlot(str, str)
    def _on_login_error(self, message: str, error_code: str):
        """Callback de erro de login."""
        logger.warning(f"Erro de login [{error_code}]: {message}")
        
        self._show_error(message)
        
        # Limpa senha por segurança
        self.pass_entry.clear()
        self.pass_entry.setFocus()
        
        # Atualiza contador de tentativas
        self._update_attempts_display(self.user_entry.text().strip().upper())
        
        self._set_ui_state(logging=False)
    
    @pyqtSlot(str)
    def _on_login_progress(self, message: str):
        """Atualiza progresso visual."""
        self.progress_bar.setFormat(message)
    
    @pyqtSlot()
    def _on_worker_finished(self):
        """Limpa worker após conclusão."""
        self.current_worker = None
        self.show_progress.emit(False)
    
    def _update_attempts_display(self, username: str):
        """Atualiza display de tentativas restantes."""
        try:
            attempts = self.user_repo._login_attempts.get(username, {"count": 0})
            remaining = max(0, 5 - attempts["count"])
            self.show_attempts.setText(f"Tentativas restantes: {remaining}")
            
            if self.user_repo._is_account_locked(username):
                lock_time = attempts.get("locked_until")
                if lock_time:
                    remaining_time = lock_time - datetime.now()
                    minutes = int(remaining_time.total_seconds() / 60)
                    self.show_attempts.setText(f"Conta bloqueada por {minutes} min")
        except:
            pass
    
    def _show_error(self, message: str, focus_widget: Optional[QWidget] = None):
        """Exibe erro com ícone e foco."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("❌ Erro de Autenticação")
        msg.setText(message)
        msg.exec_()
        
        if focus_widget:
            focus_widget.setFocus()
    
    def _show_success(self, message: str):
        """Exibe mensagem de sucesso."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("✅ Sucesso")
        msg.setText(message)
        msg.exec_()
    
    def show_forgot_password(self):
        """Abre diálogo de recuperação de senha."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("Recuperação de Senha")
        msg.setText("""
        <h3>Usuários de Demonstração:</h3>
        <p><b>LUCAS</b> - Senha: 123456 (Admin)</p>
        <p><b>ADMIN</b> - Senha: 123456 (Super Admin)</p>
        <p><b>OPERADOR</b> - Senha: 123456 (Operador)</p>
        <p><b>TESTE</b> - Senha: 123456 (Visualizador)</p>
        <hr>
        <p>Em produção, entre em contato com o administrador do sistema.</p>
        """)
        msg.exec_()
    
    def save_preferences(self, username: str, remember: bool):
        """Salva preferências do usuário."""
        prefs = {
            "last_username": username,
            "remember_me": remember,
            "timestamp": datetime.now().isoformat()
        }
        # Em produção, salvaria em config/arquivo seguro
        logger.info(f"Preferências salvas: {prefs}")
    
    def load_preferences(self):
        """Carrega preferências salvas."""
        # Preenche automaticamente com usuário de demonstração
        self.user_entry.setText("LUCAS")
        self.pass_entry.setText("123456")
        logger.info("Credenciais de demonstração pré-carregadas")
    
    def closeEvent(self, event):
        """Limpa dados sensíveis ao fechar."""
        if self.pass_entry.text():
            self.pass_entry.clear()
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.quit()
            self.current_worker.wait(1000)
        event.accept()


# =========================================================
# TESTE RÁPIDO DA TELA DE LOGIN
# =========================================================

if __name__ == "__main__":
    import sys
    
    # Configura logging para ver detalhes
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    app = QApplication(sys.argv)
    
    # Cria e mostra a tela de login
    login_page = LoginPage()
    login_page.show()
    
    # Conecta sinal de sucesso para fechar aplicação (em teste)
    def on_login_success(user_data):
        print(f"✅ Login bem-sucedido! Dados: {user_data}")
        QTimer.singleShot(2000, app.quit)  # Fecha após 2 segundos em modo teste
    
    login_page.login_successful.connect(on_login_success)
    
    sys.exit(app.exec_())