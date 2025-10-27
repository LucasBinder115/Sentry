"""
Sistema principal SENTRY.INC - Sistema de Controle de Acesso Veicular

Este módulo é o ponto de entrada principal da aplicação, responsável por:
- Configurar o ambiente e caminhos
- Inicializar a aplicação PyQt5
- Gerenciar o ciclo de vida da aplicação
- Coordenar as diferentes telas (splash, login, dashboard)
- Integrar com o sistema de configuração centralizado
"""

import sys
import os
import logging
from pathlib import Path
from PyQt5 import QtWidgets, QtCore, QtGui

# ============================================================================
# CONFIGURAÇÃO DE CAMINHOS E AMBIENTE
# ============================================================================

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ============================================================================
# IMPORTAÇÕES DO SISTEMA DE CONFIGURAÇÃO
# ============================================================================

try:
    from sentry.config import get_config, Config, Environment
    config = get_config()
except ImportError as e:
    logging.critical(f"Sistema de configuração não encontrado: {e}")
    sys.exit(1)

# Helper functions to lazily import UI components. This keeps top-level imports
# light and avoids noisy try/except blocks at module import time.

def _import_splash_class():
    try:
        from sentry.ui.views.splash import ModernSplashScreen
        return ModernSplashScreen
    except Exception as e:
        logging.warning(f"ModernSplashScreen não disponível: {e}")

        class ModernSplashScreen(QtWidgets.QSplashScreen):
            def __init__(self):
                super().__init__()
                pixmap = QtGui.QPixmap(400, 300)
                pixmap.fill(QtCore.Qt.darkBlue)
                self.setPixmap(pixmap)
                self.showMessage(
                    "SENTRY.INC\nCarregando...",
                    QtCore.Qt.AlignCenter | QtCore.Qt.AlignBottom,
                    QtCore.Qt.white,
                )

        return ModernSplashScreen


def _import_login_class():
    try:
        from sentry.ui.views.login import LoginPage
        return LoginPage
    except Exception as e:
        logging.warning(f"LoginPage não disponível: {e}")

        class LoginPage(QtWidgets.QWidget):
            login_successful = QtCore.pyqtSignal(dict)

            def __init__(self):
                super().__init__()
                layout = QtWidgets.QVBoxLayout(self)
                layout.setAlignment(QtCore.Qt.AlignCenter)

                title = QtWidgets.QLabel("SENTRY.INC - Login")
                title.setStyleSheet("font-size: 24px; font-weight: bold; color: #1a237e;")
                title.setAlignment(QtCore.Qt.AlignCenter)

                self.username_input = QtWidgets.QLineEdit()
                self.username_input.setPlaceholderText("Usuário")
                self.username_input.setFixedWidth(300)

                self.password_input = QtWidgets.QLineEdit()
                self.password_input.setPlaceholderText("Senha")
                self.password_input.setEchoMode(QtWidgets.QLineEdit.Password)
                self.password_input.setFixedWidth(300)

                login_btn = QtWidgets.QPushButton("Entrar")
                login_btn.setFixedWidth(300)
                login_btn.clicked.connect(self.do_login)

                layout.addWidget(title)
                layout.addSpacing(20)
                layout.addWidget(self.username_input, alignment=QtCore.Qt.AlignCenter)
                layout.addWidget(self.password_input, alignment=QtCore.Qt.AlignCenter)
                layout.addWidget(login_btn, alignment=QtCore.Qt.AlignCenter)

            def do_login(self):
                user = {
                    "username": self.username_input.text() or "admin",
                    "nome_completo": "Administrador do Sistema",
                    "email": "admin@sentry.inc",
                    "nivel_acesso": "admin",
                }
                self.login_successful.emit(user)

        return LoginPage


def _import_dashboard_class():
    try:
        from sentry.ui.views.dashboard import Dashboard
        return Dashboard
    except Exception as e:
        logging.warning(f"Dashboard não disponível: {e}")

        class Dashboard(QtWidgets.QWidget):
            logout_signal = QtCore.pyqtSignal()

            def __init__(self, user):
                super().__init__()
                layout = QtWidgets.QVBoxLayout(self)
                label = QtWidgets.QLabel(
                    f"Dashboard Placeholder\nUsuário: {user.get('nome_completo', 'Desconhecido')}"
                )
                label.setAlignment(QtCore.Qt.AlignCenter)
                label.setStyleSheet("font-size: 16px; font-weight: bold;")
                layout.addWidget(label)

                logout_btn = QtWidgets.QPushButton("Logout")
                logout_btn.clicked.connect(self.logout_signal.emit)
                layout.addWidget(logout_btn, alignment=QtCore.Qt.AlignCenter)

        return Dashboard

# ============================================================================
# IMPORTAÇÕES DA CAMADA DE INFRAESTRUTURA
# ============================================================================

try:
    from sentry.infra.services.camera_adapter import CameraAdapter
    from sentry.infra.services.ocr_service import OCRService
except ImportError as e:
    logging.warning(f"Serviços de infraestrutura não encontrados: {e}")
    CameraAdapter = None
    OCRService = None

# ============================================================================
# INICIALIZAÇÃO DE COMPONENTES OCR
# ============================================================================

def initialize_ocr_components():
    """
    Inicializa os componentes de OCR e câmera se disponíveis.
    Retorna uma tupla (presenter, view) ou (None, None) se não disponível.
    """
    # Try to import the optional OCR/camera components lazily. If any
    # import or initialization step fails, return (None, None) so the
    # application can continue operating without camera/OCR features.
    try:
        from sentry.ui.views.ocr_camera_view import OCRCameraView
        from sentry.ui.presenters.ocr_camera_presenter import OCRCameraPresenter
    except Exception as e:
        logging.warning(f"OCR UI components not available: {e}")
        return None, None

    try:
        from sentry.infra.services.camera_adapter import CameraAdapter
        from sentry.infra.services.ocr_service import OCRService
    except Exception as e:
        logging.warning(f"OCR infrastructure services not available: {e}")
        return None, None

    try:
        camera = CameraAdapter()
        ocr = OCRService()
        view = OCRCameraView()
        presenter = OCRCameraPresenter(view, camera, ocr)

        logging.info("Componentes OCR inicializados com sucesso")
        return presenter, view
    except Exception as e:
        logging.error(f"Erro ao inicializar componentes OCR: {e}")
        return None, None

# ============================================================================
# APLICAÇÃO PRINCIPAL
# ============================================================================

class MainApplication(QtWidgets.QMainWindow):
    """Janela principal da aplicação SENTRY.INC"""
    
    def __init__(self):
        super().__init__()
        
        self.config = get_config()
        self.usuario_logado = None
        self.current_widget = None
        self.splash = None
        self.login_page = None
        self.ocr_presenter = None
        self.ocr_view = None
        
        self._configure_window()
        self._apply_global_style()
        self._initialize_ocr()
        self.show_splash()
        
        logging.info("MainApplication inicializada")

    def _configure_window(self):
        """Configura as propriedades da janela principal"""
        self.setWindowTitle("SENTRY.INC - Sistema de Controle de Acesso")
        self.setGeometry(100, 100, self.config.ui.window_width, self.config.ui.window_height)
        self.setMinimumSize(self.config.ui.window_min_width, self.config.ui.window_min_height)
        
        icon_path = os.path.join(project_root, "resources", "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))
        
        self._center_window()

    def _center_window(self):
        """Centraliza a janela na tela"""
        try:
            screen = QtWidgets.QApplication.primaryScreen()
            if screen:
                screen_geometry = screen.availableGeometry()
            else:
                screen_geometry = QtWidgets.QDesktopWidget().availableGeometry()
        except AttributeError:
            screen_geometry = QtWidgets.QDesktopWidget().availableGeometry()

        window_geometry = self.frameGeometry()
        center_point = screen_geometry.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())

    def _apply_global_style(self):
        """Aplica estilo global à aplicação baseado na configuração"""
        global_style = f"""
        QMainWindow {{
            background-color: {self.config.ui.secondary_color};
            font-family: "{self.config.ui.font_family}";
            font-size: {self.config.ui.font_size}px;
        }}
        QMessageBox {{
            background-color: white;
        }}
        QMessageBox QLabel {{
            color: #333;
            font-size: {self.config.ui.font_size}px;
        }}
        QMessageBox QPushButton {{
            min-width: 80px;
            padding: 6px 12px;
            border-radius: 4px;
            font-weight: bold;
            background-color: {self.config.ui.primary_color};
            color: white;
        }}
        QPushButton {{
            background-color: {self.config.ui.primary_color};
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: #0d47a1;
        }}
        QLineEdit {{
            padding: 8px;
            border: 2px solid #ddd;
            border-radius: 4px;
            font-size: {self.config.ui.font_size}px;
        }}
        QLineEdit:focus {{
            border-color: {self.config.ui.primary_color};
        }}
        """
        self.setStyleSheet(global_style)

    def _initialize_ocr(self):
        """Inicializa componentes OCR"""
        self.ocr_presenter, self.ocr_view = initialize_ocr_components()
        
        if self.ocr_presenter:
            self.ocr_presenter.start_camera()
            logging.info("Câmera OCR iniciada")

    def show_splash(self):
        """Exibe a tela de splash"""
        if self.centralWidget():
            self.centralWidget().deleteLater()
        SplashClass = _import_splash_class()
        self.splash = SplashClass()
        self.show()
        self.splash.show()
        
        QtWidgets.QApplication.processEvents()
        QtCore.QTimer.singleShot(self.config.ui.splash_duration_ms, self.transition_to_login)

    def transition_to_login(self):
        """Transição suave do splash para login"""
        if hasattr(self, 'splash') and self.splash:
            self.splash.close()
            self.splash.deleteLater()
            self.splash = None
        
        self.show_login()

    def show_login(self):
        """Exibe a tela de login"""
        self.usuario_logado = None
        
        if self.centralWidget():
            self.centralWidget().deleteLater()
        LoginClass = _import_login_class()
        self.login_page = LoginClass()
        self.setCentralWidget(self.login_page)
        # Some fallback login widgets may not expose the same signal name; guard it.
        if hasattr(self.login_page, 'login_successful'):
            try:
                self.login_page.login_successful.connect(self.handle_login_success)
            except Exception:
                logging.debug('login_successful signal not connectable on login_page')
        self.setWindowTitle("SENTRY.INC - Login")

    def handle_login_success(self, usuario):
        """Trata login bem-sucedido"""
        logging.info(f"Login bem-sucedido: {usuario.get('username', 'Desconhecido')}")
        self.show_dashboard(usuario)

    def show_dashboard(self, usuario):
        """Exibe o dashboard após login"""
        if self.centralWidget():
            self.centralWidget().deleteLater()
            
        try:
            self.usuario_logado = usuario
            DashboardClass = _import_dashboard_class()
            self.current_widget = DashboardClass(usuario)
            self.setCentralWidget(self.current_widget)
            
            if hasattr(self.current_widget, 'logout_signal'):
                self.current_widget.logout_signal.connect(self.handle_logout)
            
            nome_usuario = usuario.get('nome_completo', usuario.get('username', 'Usuário'))
            self.setWindowTitle(f"SENTRY.INC - Dashboard | {nome_usuario}")
            
            logging.info(f"Dashboard carregado para: {usuario.get('username', 'Desconhecido')}")
            
        except Exception as e:
            logging.error(f"Erro ao carregar dashboard: {e}", exc_info=True)
            
            QtWidgets.QMessageBox.critical(
                self, 
                "Erro Fatal", 
                f"Erro ao carregar dashboard.\n\nDetalhes: {str(e)}\n\nO sistema será reiniciado."
            )
            
            self.show_login()

    def handle_logout(self):
        """Trata logout do usuário"""
        if self.usuario_logado:
            nome = self.usuario_logado.get('nome_completo', self.usuario_logado.get('username', 'Desconhecido'))
            
            reply = QtWidgets.QMessageBox.question(
                self, 
                "Confirmar Logout",
                f"Deseja realmente fazer logout?\n\nUsuário: {nome}",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            
            if reply == QtWidgets.QMessageBox.Yes:
                logging.info(f"Logout realizado: {self.usuario_logado.get('username', 'Desconhecido')}")
                self.perform_logout()
        else:
            self.show_login()

    def perform_logout(self):
        """Executa o logout"""
        self.usuario_logado = None
        
        if self.current_widget:
            self.current_widget.deleteLater()
            self.current_widget = None
        
        self.show_login()

    def closeEvent(self, event):
        """Intercepta fechamento da janela"""
        if self.usuario_logado:
            reply = QtWidgets.QMessageBox.question(
                self, 
                "Fechar Sistema",
                "Deseja realmente fechar o sistema SENTRY.INC?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            
            if reply == QtWidgets.QMessageBox.Yes:
                logging.info("Sistema encerrado pelo usuário")
                event.accept()
            else:
                event.ignore()
        else:
            logging.info("Sistema encerrado")
            event.accept()

    def get_current_user(self):
        """Retorna os dados do usuário logado"""
        return self.usuario_logado

    def update_user_info(self, usuario):
        """Atualiza os dados do usuário logado"""
        self.usuario_logado = usuario
        
        if usuario:
            nome = usuario.get('nome_completo', usuario.get('username', 'Usuário'))
            self.setWindowTitle(f"SENTRY.INC - Dashboard | {nome}")
        
        logging.info("Informações do usuário atualizadas")

    def restart_application(self):
        """Reinicia a aplicação (volta ao splash)"""
        reply = QtWidgets.QMessageBox.question(
            self, 
            "Reiniciar Sistema",
            "Deseja reiniciar o sistema SENTRY.INC?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            logging.info("Reiniciando sistema")
            self.usuario_logado = None
            
            if self.centralWidget():
                self.centralWidget().deleteLater()
            
            self.show_splash()

    def show_about(self):
        """Mostra informações sobre o sistema"""
        about_text = """
        <h2>SENTRY.INC</h2>
        <p><b>Sistema de Controle de Acesso Veicular</b></p>
        <p>Versão: 2.0.0</p>
        <hr>
        <p><b>Funcionalidades:</b></p>
        <ul>
            <li>Reconhecimento de Placas (OCR)</li>
            <li>Captura de Fotos</li>
            <li>Consulta NHTSA (Recalls)</li>
            <li>Histórico e Relatórios</li>
        </ul>
        <hr>
        <p><b>Tecnologias:</b></p>
        <ul>
            <li>PyQt5 - Interface Gráfica</li>
            <li>OpenCV - Visão Computacional</li>
            <li>EasyOCR - Reconhecimento de Texto</li>
            <li>NHTSA API - Dados de Segurança</li>
        </ul>
        <hr>
        <p style='text-align: center; color: #666;'>
            © 2025 SENTRY.INC - Todos os direitos reservados
        </p>
        """
        
        QtWidgets.QMessageBox.about(self, "Sobre SENTRY.INC", about_text)


# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

def main():
    """Função principal para iniciar a aplicação"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logging.info("Iniciando SENTRY.INC - Sistema de Controle de Acesso")
    
    app_config = get_config()
    app = QtWidgets.QApplication(sys.argv)
    app.setFont(QtGui.QFont(app_config.ui.font_family, app_config.ui.font_size))
    app.setOrganizationName("SENTRY.INC")
    app.setApplicationName("Sistema de Controle de Acesso")
    
    try:
        window = MainApplication()
        logging.info("Janela principal criada com sucesso")
    except Exception as e:
        logging.critical(f"Erro ao criar janela principal: {e}", exc_info=True)
        sys.exit(1)
    
    logging.info("Sistema SENTRY.INC iniciado com sucesso")
    exit_code = app.exec_()
    
    logging.info("Sistema SENTRY.INC encerrado")
    sys.exit(exit_code)


# ============================================================================
# PONTO DE ENTRADA
# ============================================================================

if __name__ == "__main__":
    main()