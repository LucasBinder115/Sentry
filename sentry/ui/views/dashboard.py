# LOGISICA/sentry/ui/views/dashboard.py

import sys
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict

# Imports do PyQt5
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QTextEdit, QListWidget, QListWidgetItem,
                            QSplitter, QTabWidget, QFrame, QMessageBox, QFileDialog,
                            QScrollArea, QSizePolicy, QLineEdit, QGroupBox, QTableWidget,
                            QTableWidgetItem, QHeaderView, QProgressBar, QMenu, QAction,
                            QComboBox, QDateEdit, QGridLayout, QToolButton, QSystemTrayIcon,
                            QToolBar, QStackedWidget)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize, pyqtSlot, QDate, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QPixmap, QImage, QFont, QColor, QPalette, QIcon, QPainter, QBrush, QPen

# Imports de outras Views do mesmo módulo
from sentry.ui.views.vehicle_registration_view import VehicleRegistrationView
from sentry.ui.views.merchandise_registration_view import MerchandiseRegistrationView
from sentry.ui.views.carrier_registration_view import CarrierRegistrationView
from sentry.ui.views.export_view import ExportView
from sentry.ui.widgets.vehicle_query_widget import VehicleQueryWidget

# Imports dos Presenters
try:
    from sentry.ui.presenters.dashboard_presenter import create_dashboard_presenter
except ImportError:
    print("DashboardPresenter não encontrado, usando factory simplificada")
    def create_dashboard_presenter(view):
        class EmergencyPresenter:
            def __init__(self, view):
                self.view = view
            def perform_safety_check(self, plate: str):
                result = {"plate": plate, "status": "EMERGENCY_MODE", "message": "Sistema em modo de emergência"}
                if hasattr(self.view, 'show_safety_check_result'):
                    self.view.show_safety_check_result(result)
            def load_initial_data(self):
                pass
        return EmergencyPresenter(view)

# Imports de Entidades
from sentry.core.entities.vehicle import Vehicle
from sentry.core.entities.access_log import AccessLog


class StatisticCard(QFrame):
    """Widget para exibir cards de estatísticas."""
    
    clicked = pyqtSignal()
    
    def __init__(self, title: str, value: str = "0", subtitle: str = "", color: str = "#2C3E50", parent=None):
        super().__init__(parent)
        self.setup_ui(title, value, subtitle, color)
        self.setStyleSheet(f"""
            StatisticCard {{
                background-color: white;
                border-left: 4px solid {color};
                border-radius: 4px;
                padding: 20px;
            }}
            StatisticCard:hover {{
                background-color: #F8F9FA;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
        """)
        self.setCursor(Qt.PointingHandCursor)
        
    def setup_ui(self, title: str, value: str, subtitle: str, color: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # Título
        title_label = QLabel(title.upper())
        title_label.setFont(QFont("Segoe UI", 9))
        title_label.setStyleSheet("color: #6C757D; font-weight: 600; letter-spacing: 0.5px;")
        layout.addWidget(title_label)
        
        # Valor
        self.value_label = QLabel(value)
        self.value_label.setFont(QFont("Segoe UI", 28, QFont.Bold))
        self.value_label.setStyleSheet(f"color: {color};")
        layout.addWidget(self.value_label)
        
        # Subtítulo
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setFont(QFont("Segoe UI", 8))
            subtitle_label.setStyleSheet("color: #ADB5BD;")
            layout.addWidget(subtitle_label)
        
        self.setMinimumHeight(120)
        self.setMaximumHeight(140)
        
    def update_value(self, new_value: str):
        """Atualiza o valor do card."""
        self.value_label.setText(new_value)
        
    def mousePressEvent(self, event):
        """Emite sinal quando clicado."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ActivityFeed(QFrame):
    """Widget para exibir feed de atividades recentes."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        self.setStyleSheet("""
            ActivityFeed {
                background-color: white;
                border-radius: 4px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setStyleSheet("background-color: #F8F9FA; padding: 15px; border-bottom: 1px solid #DEE2E6;")
        header_layout = QHBoxLayout(header)
        header_label = QLabel("Atividades Recentes")
        header_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        header_label.setStyleSheet("color: #212529;")
        header_layout.addWidget(header_label)
        layout.addWidget(header)
        
        # Lista de atividades
        self.activity_list = QListWidget()
        self.activity_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: white;
            }
            QListWidget::item {
                padding: 12px 15px;
                border-bottom: 1px solid #F1F3F5;
            }
            QListWidget::item:hover {
                background-color: #F8F9FA;
            }
        """)
        layout.addWidget(self.activity_list)
        
    def add_activity(self, activity_type: str, description: str, timestamp: str = None):
        """Adiciona uma nova atividade ao feed."""
        if timestamp is None:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
        # Mapeamento de tipos para indicadores visuais
        indicators = {
            "vehicle": "🚗",
            "merchandise": "📦",
            "carrier": "🏢",
            "export": "💾",
            "access": "🚪",
            "alert": "⚠️",
            "success": "✅",
            "error": "❌"
        }
        
        colors = {
            "vehicle": "#3498DB",
            "merchandise": "#9B59B6",
            "carrier": "#E67E22",
            "export": "#1ABC9C",
            "access": "#34495E",
            "alert": "#F39C12",
            "success": "#27AE60",
            "error": "#E74C3C"
        }
        
        indicator = indicators.get(activity_type, "•")
        color = colors.get(activity_type, "#6C757D")
        
        item = QListWidgetItem()
        
        # Widget customizado para o item
        widget = QWidget()
        widget_layout = QHBoxLayout(widget)
        widget_layout.setContentsMargins(0, 0, 0, 0)
        
        # Indicador colorido
        indicator_label = QLabel(indicator)
        indicator_label.setFont(QFont("Segoe UI", 12))
        indicator_label.setStyleSheet(f"color: {color}; padding-right: 8px;")
        indicator_label.setFixedWidth(30)
        widget_layout.addWidget(indicator_label)
        
        # Conteúdo
        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)
        
        desc_label = QLabel(description)
        desc_label.setFont(QFont("Segoe UI", 9))
        desc_label.setStyleSheet("color: #495057;")
        desc_label.setWordWrap(True)
        content_layout.addWidget(desc_label)
        
        time_label = QLabel(timestamp)
        time_label.setFont(QFont("Segoe UI", 8))
        time_label.setStyleSheet("color: #ADB5BD;")
        content_layout.addWidget(time_label)
        
        widget_layout.addLayout(content_layout, 1)
        
        item.setSizeHint(widget.sizeHint())
        self.activity_list.insertItem(0, item)
        self.activity_list.setItemWidget(item, widget)
        
        # Limita a 50 itens
        if self.activity_list.count() > 50:
            self.activity_list.takeItem(self.activity_list.count() - 1)


class Dashboard(QMainWindow):
    """
    Tela principal (Dashboard) do sistema SENTRY.
    Design moderno com menus superiores organizados.
    """
    
    logout_signal = pyqtSignal()
    refresh_data_signal = pyqtSignal()

    def __init__(self, usuario, parent=None):
        super().__init__(parent)
        self.usuario = usuario
        
        # Inicialização do Presenter
        self.presenter = create_dashboard_presenter(self)
        
        # Estado da aplicação
        self.current_filter = "all"
        self.search_term = ""
        self.is_fullscreen = False
        self.current_section = "dashboard"  # Seção atual
        
        # Views abertas
        self.open_views = []

        self.setWindowTitle(f"SENTRY - Sistema de Controle Logístico | {self.usuario.get('username', 'N/A')}")
        self.setGeometry(100, 100, 1600, 900)
        self.setMinimumSize(1200, 700)

        # Aplicar tema moderno
        self.apply_modern_theme()
        
        # INICIALIZAR menu_buttons ANTES de setup_ui
        self.menu_buttons = {}
        
        self.setup_ui()
        self.setup_top_menu_bar()
        self.setup_status_bar()
        self.setup_shortcuts()
        self.setup_auto_refresh()
        
        # Carregar dados iniciais
        self.presenter.load_initial_data()
        
        # Adicionar notificação de boas-vindas
        self.show_welcome_message()

    def apply_modern_theme(self):
        """Aplica tema moderno e profissional."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5F6FA;
            }
            QGroupBox {
                font-weight: 600;
                font-size: 11pt;
                border: 1px solid #E1E4E8;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: #2C3E50;
            }
            QPushButton {
                background-color: #2C3E50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: 600;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #34495E;
            }
            QPushButton:pressed {
                background-color: #1A252F;
            }
            QPushButton:disabled {
                background-color: #95A5A6;
                color: #BDC3C7;
            }
            QLineEdit, QComboBox, QDateEdit {
                padding: 8px 12px;
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                background-color: white;
                font-size: 10pt;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
                border: 1px solid #3498DB;
                outline: none;
            }
            QTableWidget {
                border: 1px solid #E1E4E8;
                border-radius: 4px;
                background-color: white;
                gridline-color: #F1F3F5;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #3498DB;
                color: white;
            }
            QHeaderView::section {
                background-color: #F8F9FA;
                padding: 10px;
                border: none;
                border-bottom: 2px solid #E1E4E8;
                font-weight: 600;
                color: #2C3E50;
            }
            QTabWidget::pane {
                border: 1px solid #E1E4E8;
                border-radius: 4px;
                background-color: white;
                top: -1px;
            }
            QTabBar::tab {
                background-color: transparent;
                padding: 10px 20px;
                margin-right: 4px;
                border-bottom: 2px solid transparent;
                color: #6C757D;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                color: #2C3E50;
                border-bottom: 2px solid #3498DB;
                font-weight: 600;
            }
            QTabBar::tab:hover {
                color: #495057;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #F8F9FA;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #CED4DA;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #ADB5BD;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

    def setup_top_menu_bar(self):
        """Configura a barra de menu superior com seções organizadas."""
        # Criar toolbar principal como menu superior
        top_toolbar = QToolBar("Menu Principal")
        top_toolbar.setMovable(False)
        top_toolbar.setIconSize(QSize(24, 24))
        top_toolbar.setStyleSheet("""
            QToolBar {
                background-color: #2C3E50;
                border: none;
                padding: 8px;
                spacing: 4px;
            }
            QToolButton {
                background-color: transparent;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 4px;
                font-weight: 600;
                font-size: 11pt;
                margin: 0 2px;
            }
            QToolButton:hover {
                background-color: #34495E;
            }
            QToolButton:pressed {
                background-color: #1A252F;
            }
            QToolButton[active="true"] {
                background-color: #3498DB;
                color: white;
            }
        """)
        self.addToolBar(Qt.TopToolBarArea, top_toolbar)

        # Seção DASHBOARD
        dashboard_btn = QToolButton()
        dashboard_btn.setText("📊 DASHBOARD")
        dashboard_btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        dashboard_btn.clicked.connect(lambda: self.switch_section("dashboard"))
        dashboard_btn.setProperty("active", True)
        top_toolbar.addWidget(dashboard_btn)
        self.menu_buttons["dashboard"] = dashboard_btn

        top_toolbar.addSeparator()

        # Seção VEÍCULOS
        vehicles_btn = QToolButton()
        vehicles_btn.setText("🚗 VEÍCULOS")
        vehicles_btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        vehicles_btn.clicked.connect(lambda: self.switch_section("vehicles"))
        top_toolbar.addWidget(vehicles_btn)
        self.menu_buttons["vehicles"] = vehicles_btn

        # Seção MERCADORIAS
        merchandise_btn = QToolButton()
        merchandise_btn.setText("📦 MERCADORIAS")
        merchandise_btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        merchandise_btn.clicked.connect(lambda: self.switch_section("merchandise"))
        top_toolbar.addWidget(merchandise_btn)
        self.menu_buttons["merchandise"] = merchandise_btn

        # Seção TRANSPORTADORAS
        carriers_btn = QToolButton()
        carriers_btn.setText("🏢 TRANSPORTADORAS")
        carriers_btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        carriers_btn.clicked.connect(lambda: self.switch_section("carriers"))
        top_toolbar.addWidget(carriers_btn)
        self.menu_buttons["carriers"] = carriers_btn

        top_toolbar.addSeparator()

        # Seção ACESSOS
        access_btn = QToolButton()
        access_btn.setText("🚪 ACESSOS")
        access_btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        access_btn.clicked.connect(lambda: self.switch_section("access"))
        top_toolbar.addWidget(access_btn)
        self.menu_buttons["access"] = access_btn

        # Seção RELATÓRIOS
        reports_btn = QToolButton()
        reports_btn.setText("📈 RELATÓRIOS")
        reports_btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        reports_btn.clicked.connect(lambda: self.switch_section("reports"))
        top_toolbar.addWidget(reports_btn)
        self.menu_buttons["reports"] = reports_btn

        top_toolbar.addSeparator()

        # Seção CONFIGURAÇÕES
        settings_btn = QToolButton()
        settings_btn.setText("⚙️ CONFIGURAÇÕES")
        settings_btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        settings_btn.clicked.connect(lambda: self.switch_section("settings"))
        top_toolbar.addWidget(settings_btn)
        self.menu_buttons["settings"] = settings_btn

        # Espaço flexível
        top_toolbar.addWidget(QWidget())

        # Botão do usuário
        user_btn = QToolButton()
        user_btn.setText(f"👤 {self.usuario.get('username', 'Usuário').upper()}")
        user_btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        user_btn.setPopupMode(QToolButton.InstantPopup)
        
        user_menu = QMenu(self)
        user_menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #E1E4E8;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 24px;
                color: #2C3E50;
            }
            QMenu::item:selected {
                background-color: #F8F9FA;
            }
        """)
        
        profile_action = QAction("👤 Meu Perfil", self)
        user_menu.addAction(profile_action)
        
        user_menu.addSeparator()
        
        logout_action = QAction("🚪 Sair", self)
        logout_action.triggered.connect(self.logout)
        user_menu.addAction(logout_action)
        
        user_btn.setMenu(user_menu)
        top_toolbar.addWidget(user_btn)

        self.top_toolbar = top_toolbar

    def switch_section(self, section_name):
        """Alterna entre as seções do sistema."""
        self.current_section = section_name
        
        # Atualizar estado dos botões
        for name, button in self.menu_buttons.items():
            button.setProperty("active", name == section_name)
            button.style().polish(button)  # Forçar atualização do estilo
        
        # Atualizar conteúdo baseado na seção
        self.update_section_content(section_name)
        
        # Adicionar atividade ao feed
        section_names = {
            "dashboard": "Dashboard Principal",
            "vehicles": "Gestão de Veículos",
            "merchandise": "Gestão de Mercadorias", 
            "carriers": "Gestão de Transportadoras",
            "access": "Controle de Acessos",
            "reports": "Relatórios e Análises",
            "settings": "Configurações do Sistema"
        }
        
        if hasattr(self, 'activity_feed'):
            self.activity_feed.add_activity(
                "success", 
                f"Navegou para: {section_names.get(section_name, section_name)}"
            )

    def update_section_content(self, section_name):
        """Atualiza o conteúdo baseado na seção selecionada."""
        # Limpar conteúdo atual
        for i in reversed(range(self.main_content_layout.count())):
            widget = self.main_content_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # Adicionar conteúdo específico da seção
        if section_name == "dashboard":
            self.setup_dashboard_content()
        elif section_name == "vehicles":
            self.setup_vehicles_section()
        elif section_name == "merchandise":
            self.setup_merchandise_section()
        elif section_name == "carriers":
            self.setup_carriers_section()
        elif section_name == "access":
            self.setup_access_section()
        elif section_name == "reports":
            self.setup_reports_section()
        elif section_name == "settings":
            self.setup_settings_section()

    def setup_dashboard_content(self):
        """Configura o conteúdo do dashboard principal."""
        # Container principal do dashboard
        dashboard_container = QWidget()
        dashboard_layout = QVBoxLayout(dashboard_container)
        dashboard_layout.setSpacing(20)
        
        # Seção de métricas
        metrics_widget = self.create_metrics_section()
        dashboard_layout.addWidget(metrics_widget)
        
        # Seção principal (logs + atividades)
        main_content_split = QSplitter(Qt.Horizontal)
        
        # Painel esquerdo - Logs de acesso
        left_panel = self.create_access_logs_section()
        main_content_split.addWidget(left_panel)
        
        # Painel direito - Atividades e consulta
        right_panel = self.create_right_panel()
        main_content_split.addWidget(right_panel)
        
        # Configurar proporções
        main_content_split.setSizes([700, 400])
        main_content_split.setStyleSheet("QSplitter::handle { background-color: #E1E4E8; }")
        
        dashboard_layout.addWidget(main_content_split, 1)
        
        self.main_content_layout.addWidget(dashboard_container)

    def create_metrics_section(self):
        """Cria a seção de métricas do dashboard."""
        metrics_widget = QWidget()
        metrics_layout = QHBoxLayout(metrics_widget)
        metrics_layout.setSpacing(15)
        
        # Cards de métricas
        metrics_data = [
            ("Total de Veículos", "156", "#3498DB", "+12 este mês"),
            ("Veículos no Pátio", "24", "#2ECC71", "8 entradas hoje"),
            ("Alertas Ativos", "3", "#E74C3C", "2 críticos"),
            ("Mercadorias", "89", "#9B59B6", "15 novas"),
            ("Transportadoras", "42", "#E67E22", "3 parceiras")
        ]
        
        for title, value, color, subtitle in metrics_data:
            card = StatisticCard(title, value, subtitle, color)
            metrics_layout.addWidget(card)
        
        return metrics_widget

    def create_access_logs_section(self):
        """Cria a seção de logs de acesso."""
        logs_frame = QFrame()
        logs_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 4px;
            }
        """)
        
        logs_layout = QVBoxLayout(logs_frame)
        logs_layout.setContentsMargins(0, 0, 0, 0)
        logs_layout.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setStyleSheet("background-color: #F8F9FA; padding: 15px; border-bottom: 1px solid #DEE2E6;")
        header_layout = QHBoxLayout(header)
        
        title_label = QLabel("Logs de Acesso Recentes")
        title_label.setFont(QFont("Segoe UI", 11, QFont.Bold))
        title_label.setStyleSheet("color: #212529;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Botão de atualizar
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(30, 30)
        refresh_btn.setStyleSheet("QPushButton { border: none; background: transparent; }")
        refresh_btn.clicked.connect(self.refresh_dashboard)
        header_layout.addWidget(refresh_btn)
        
        logs_layout.addWidget(header)
        
        # Tabela de logs
        self.logs_table = QTableWidget()
        self.logs_table.setColumnCount(5)
        self.logs_table.setHorizontalHeaderLabels(["Placa", "Tipo", "Motorista", "Horário", "Status"])
        self.logs_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Dados mock para demonstração
        mock_data = [
            ["ABC1234", "ENTRADA", "João Silva", "10:30:15", "✅"],
            ["XYZ5678", "SAÍDA", "Maria Santos", "10:25:42", "✅"],
            ["DEF9012", "ENTRADA", "Pedro Costa", "10:15:18", "✅"],
            ["GHI3456", "ENTRADA", "Ana Oliveira", "09:58:33", "⚠️"],
            ["JKL7890", "SAÍDA", "Carlos Lima", "09:45:21", "✅"]
        ]
        
        self.logs_table.setRowCount(len(mock_data))
        for row, data in enumerate(mock_data):
            for col, value in enumerate(data):
                item = QTableWidgetItem(str(value))
                self.logs_table.setItem(row, col, item)
        
        logs_layout.addWidget(self.logs_table)
        
        return logs_frame

    def create_right_panel(self):
        """Cria o painel direito (atividades + consulta)."""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(20)
        
        # Widget de consulta de veículos
        query_group = QGroupBox("🔍 Consulta de Segurança")
        query_layout = QVBoxLayout(query_group)
        
        self.vehicle_query_widget = VehicleQueryWidget()
        self.vehicle_query_widget.query_requested.connect(self.presenter.perform_safety_check)
        query_layout.addWidget(self.vehicle_query_widget)
        
        right_layout.addWidget(query_group)
        
        # Feed de atividades
        self.activity_feed = ActivityFeed()
        right_layout.addWidget(self.activity_feed, 1)
        
        return right_widget

    def setup_vehicles_section(self):
        """Configura a seção de veículos."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Header da seção
        header = QLabel("🚗 GESTÃO DE VEÍCULOS")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #2C3E50; margin: 20px 0;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # Cards de ação
        actions_layout = QHBoxLayout()
        
        # Card Registrar Veículo
        register_card = QFrame()
        register_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3498DB, stop:1 #2980B9);
                border-radius: 8px;
                padding: 30px;
            }
        """)
        register_layout = QVBoxLayout(register_card)
        register_icon = QLabel("🚗")
        register_icon.setFont(QFont("Segoe UI", 24))
        register_icon.setAlignment(Qt.AlignCenter)
        register_layout.addWidget(register_icon)
        
        register_title = QLabel("Registrar Veículo")
        register_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        register_title.setStyleSheet("color: white;")
        register_title.setAlignment(Qt.AlignCenter)
        register_layout.addWidget(register_title)
        
        register_btn = QPushButton("Abrir Cadastro")
        register_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #3498DB;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F8F9FA;
            }
        """)
        register_btn.clicked.connect(self.open_vehicle_registration)
        register_layout.addWidget(register_btn)
        
        actions_layout.addWidget(register_card)
        
        # Card Consultar Veículo
        query_card = QFrame()
        query_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2ECC71, stop:1 #27AE60);
                border-radius: 8px;
                padding: 30px;
            }
        """)
        query_layout = QVBoxLayout(query_card)
        query_icon = QLabel("🔍")
        query_icon.setFont(QFont("Segoe UI", 24))
        query_icon.setAlignment(Qt.AlignCenter)
        query_layout.addWidget(query_icon)
        
        query_title = QLabel("Consultar Segurança")
        query_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        query_title.setStyleSheet("color: white;")
        query_title.setAlignment(Qt.AlignCenter)
        query_layout.addWidget(query_title)
        
        # Adicionar widget de consulta
        query_widget = VehicleQueryWidget()
        query_widget.query_requested.connect(self.presenter.perform_safety_check)
        query_layout.addWidget(query_widget)
        
        actions_layout.addWidget(query_card)
        
        layout.addLayout(actions_layout)
        
        # Tabela de veículos recentes
        vehicles_table_label = QLabel("Veículos Recentes")
        vehicles_table_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        vehicles_table_label.setStyleSheet("color: #2C3E50; margin-top: 20px;")
        layout.addWidget(vehicles_table_label)
        
        vehicles_table = QTableWidget()
        vehicles_table.setColumnCount(5)
        vehicles_table.setHorizontalHeaderLabels(["Placa", "Modelo", "Transportadora", "Status", "Último Acesso"])
        vehicles_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Dados mock
        mock_vehicles = [
            ["ABC1234", "Volvo FH", "Transportes Binder", "DENTRO", "10:30"],
            ["XYZ5678", "Mercedes Actros", "Logística Express", "FORA", "09:45"],
            ["DEF9012", "Scania R500", "Cargas Rápidas", "DENTRO", "08:15"]
        ]
        
        vehicles_table.setRowCount(len(mock_vehicles))
        for row, data in enumerate(mock_vehicles):
            for col, value in enumerate(data):
                item = QTableWidgetItem(str(value))
                vehicles_table.setItem(row, col, item)
        
        layout.addWidget(vehicles_table)
        
        self.main_content_layout.addWidget(container)

    def setup_merchandise_section(self):
        """Configura a seção de mercadorias."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        header = QLabel("📦 GESTÃO DE MERCADORIAS")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #2C3E50; margin: 20px 0;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # Card de ação
        action_card = QFrame()
        action_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #9B59B6, stop:1 #8E44AD);
                border-radius: 8px;
                padding: 40px;
                max-width: 400px;
                margin: 0 auto;
            }
        """)
        action_layout = QVBoxLayout(action_card)
        
        icon = QLabel("📦")
        icon.setFont(QFont("Segoe UI", 32))
        icon.setAlignment(Qt.AlignCenter)
        action_layout.addWidget(icon)
        
        title = QLabel("Registrar Mercadoria")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: white;")
        title.setAlignment(Qt.AlignCenter)
        action_layout.addWidget(title)
        
        description = QLabel("Cadastre novas mercadorias no sistema com informações detalhadas como categoria, quantidade, valor e dados fiscais.")
        description.setFont(QFont("Segoe UI", 10))
        description.setStyleSheet("color: white; opacity: 0.9;")
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignCenter)
        action_layout.addWidget(description)
        
        register_btn = QPushButton("Abrir Cadastro de Mercadorias")
        register_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #9B59B6;
                border: none;
                padding: 12px;
                border-radius: 4px;
                font-weight: bold;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #F8F9FA;
            }
        """)
        register_btn.clicked.connect(self.open_merchandise_registration)
        action_layout.addWidget(register_btn)
        
        layout.addWidget(action_card)
        
        self.main_content_layout.addWidget(container)

    def setup_carriers_section(self):
        """Configura a seção de transportadoras."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        header = QLabel("🏢 GESTÃO DE TRANSPORTADORAS")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #2C3E50; margin: 20px 0;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # Card de ação
        action_card = QFrame()
        action_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E67E22, stop:1 #D35400);
                border-radius: 8px;
                padding: 40px;
                max-width: 400px;
                margin: 0 auto;
            }
        """)
        action_layout = QVBoxLayout(action_card)
        
        icon = QLabel("🏢")
        icon.setFont(QFont("Segoe UI", 32))
        icon.setAlignment(Qt.AlignCenter)
        action_layout.addWidget(icon)
        
        title = QLabel("Registrar Transportadora")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: white;")
        title.setAlignment(Qt.AlignCenter)
        action_layout.addWidget(title)
        
        description = QLabel("Cadastre novas transportadoras parceiras com dados completos como CNPJ, endereço, contatos e informações de operação.")
        description.setFont(QFont("Segoe UI", 10))
        description.setStyleSheet("color: white; opacity: 0.9;")
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignCenter)
        action_layout.addWidget(description)
        
        register_btn = QPushButton("Abrir Cadastro de Transportadoras")
        register_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #E67E22;
                border: none;
                padding: 12px;
                border-radius: 4px;
                font-weight: bold;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #F8F9FA;
            }
        """)
        register_btn.clicked.connect(self.open_carrier_registration)
        action_layout.addWidget(register_btn)
        
        layout.addWidget(action_card)
        
        self.main_content_layout.addWidget(container)

    def setup_access_section(self):
        """Configura a seção de acessos."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        header = QLabel("🚪 CONTROLE DE ACESSOS")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #2C3E50; margin: 20px 0;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # Métricas de acesso
        metrics_layout = QHBoxLayout()
        
        metrics_data = [
            ("Entradas Hoje", "24", "#27AE60", "↗ 12%"),
            ("Saídas Hoje", "18", "#E74C3C", "↘ 5%"),
            ("Veículos no Pátio", "8", "#3498DB", "→ Estável"),
            ("Acessos Pendentes", "2", "#F39C12", "⚠ Atenção")
        ]
        
        for title, value, color, trend in metrics_data:
            card = StatisticCard(title, value, trend, color)
            metrics_layout.addWidget(card)
        
        layout.addLayout(metrics_layout)
        
        # Tabela de acessos recentes
        access_table_label = QLabel("Registros de Acesso Recentes")
        access_table_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        access_table_label.setStyleSheet("color: #2C3E50; margin-top: 20px;")
        layout.addWidget(access_table_label)
        
        access_table = QTableWidget()
        access_table.setColumnCount(5)
        access_table.setHorizontalHeaderLabels(["Placa", "Tipo", "Motorista", "Horário", "Status"])
        access_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Dados mock
        mock_access = [
            ["ABC1234", "ENTRADA", "João Silva", "10:30:15", "✅"],
            ["XYZ5678", "SAÍDA", "Maria Santos", "10:25:42", "✅"],
            ["DEF9012", "ENTRADA", "Pedro Costa", "10:15:18", "✅"]
        ]
        
        access_table.setRowCount(len(mock_access))
        for row, data in enumerate(mock_access):
            for col, value in enumerate(data):
                item = QTableWidgetItem(str(value))
                access_table.setItem(row, col, item)
        
        layout.addWidget(access_table)
        
        self.main_content_layout.addWidget(container)

    def setup_reports_section(self):
        """Configura a seção de relatórios."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        header = QLabel("📈 RELATÓRIOS E ANÁLISES")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #2C3E50; margin: 20px 0;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # Cards de relatórios
        reports_layout = QGridLayout()
        reports_layout.setSpacing(20)
        
        reports_data = [
            ("Relatório Diário", "📊", "Relatório completo do dia", "#3498DB", 0, 0),
            ("Relatório Mensal", "📅", "Análise mensal consolidada", "#2ECC71", 0, 1),
            ("Veículos Ativos", "🚗", "Lista de veículos em operação", "#E67E22", 1, 0),
            ("Transportadoras", "🏢", "Relação de transportadoras", "#9B59B6", 1, 1),
            ("Mercadorias", "📦", "Inventário de mercadorias", "#1ABC9C", 2, 0),
            ("Exportar Dados", "💾", "Exportar dados do sistema", "#34495E", 2, 1)
        ]
        
        for title, icon, description, color, row, col in reports_data:
            card = self.create_report_card(title, icon, description, color)
            reports_layout.addWidget(card, row, col)
        
        layout.addLayout(reports_layout)
        
        self.main_content_layout.addWidget(container)

    def setup_settings_section(self):
        """Configura a seção de configurações."""
        container = QWidget()
        layout = QVBoxLayout(container)
        
        header = QLabel("⚙️ CONFIGURAÇÕES DO SISTEMA")
        header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.setStyleSheet("color: #2C3E50; margin: 20px 0;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # Cards de configuração
        settings_layout = QVBoxLayout()
        settings_layout.setSpacing(15)
        
        settings_groups = [
            ("Preferências do Usuário", ["Tema", "Idioma", "Notificações"]),
            ("Configurações do Sistema", ["Backup Automático", "Logs", "Integrações"]),
            ("Segurança", ["Senha", "Permissões", "Auditoria"])
        ]
        
        for group_title, options in settings_groups:
            group = QGroupBox(group_title)
            group_layout = QVBoxLayout(group)
            
            for option in options:
                option_layout = QHBoxLayout()
                option_label = QLabel(option)
                option_label.setFont(QFont("Segoe UI", 10))
                option_layout.addWidget(option_label)
                option_layout.addStretch()
                
                if option in ["Tema", "Idioma"]:
                    combo = QComboBox()
                    combo.addItems(["Claro", "Escuro"] if option == "Tema" else ["Português", "Inglês", "Espanhol"])
                    combo.setFixedWidth(120)
                    option_layout.addWidget(combo)
                elif option in ["Notificações", "Backup Automático"]:
                    from PyQt5.QtWidgets import QCheckBox
                    checkbox = QCheckBox()
                    checkbox.setChecked(True)
                    option_layout.addWidget(checkbox)
                
                group_layout.addLayout(option_layout)
            
            settings_layout.addWidget(group)
        
        layout.addLayout(settings_layout)
        
        self.main_content_layout.addWidget(container)

    def create_report_card(self, title, icon, description, color):
        """Cria card de relatório."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-left: 4px solid {color};
                border-radius: 4px;
                padding: 20px;
            }}
            QFrame:hover {{
                background-color: #F8F9FA;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
        """)
        card.setCursor(Qt.PointingHandCursor)
        
        layout = QVBoxLayout(card)
        
        # Header
        header_layout = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI", 16))
        header_layout.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title_label.setStyleSheet(f"color: {color};")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Descrição
        desc_label = QLabel(description)
        desc_label.setFont(QFont("Segoe UI", 9))
        desc_label.setStyleSheet("color: #6C757D;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Botão
        btn = QPushButton("Gerar Relatório")
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-size: 9pt;
                margin-top: 10px;
            }}
            QPushButton:hover {{
                background-color: #2980B9;
            }}
        """)
        btn.clicked.connect(lambda: self.generate_report(title))
        layout.addWidget(btn)
        
        return card

    def setup_ui(self):
        """Configura a interface principal."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Área de conteúdo principal
        self.main_content_widget = QWidget()
        self.main_content_layout = QVBoxLayout(self.main_content_widget)
        self.main_content_layout.setContentsMargins(20, 20, 20, 20)
        self.main_content_layout.setSpacing(0)
        
        main_layout.addWidget(self.main_content_widget)

    def setup_status_bar(self):
        """Configura a barra de status."""
        status_bar = self.statusBar()
        status_bar.showMessage(f"Sistema SENTRY - Usuário: {self.usuario.get('username', 'N/A')} | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    def setup_shortcuts(self):
        """Configura atalhos de teclado."""
        # Implementar atalhos se necessário
        pass

    def setup_auto_refresh(self):
        """Configura atualização automática."""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_dashboard)
        self.refresh_timer.start(30000)  # 30 segundos

    def refresh_dashboard(self):
        """Atualiza o dashboard."""
        self.presenter.load_initial_data()
        self.statusBar().showMessage(f"Dados atualizados | {datetime.now().strftime('%H:%M:%S')}")
        
        if hasattr(self, 'activity_feed'):
            self.activity_feed.add_activity("success", "Dashboard atualizado automaticamente")

    def open_vehicle_registration(self):
        """Abre a tela de registro de veículos."""
        try:
            view = VehicleRegistrationView(self)
            view.show()
            self.open_views.append(view)
            if hasattr(self, 'activity_feed'):
                self.activity_feed.add_activity("vehicle", "Aberto cadastro de veículo")
        except Exception as e:
            self.show_error(f"Erro ao abrir cadastro de veículo: {e}")

    def open_merchandise_registration(self):
        """Abre a tela de registro de mercadorias."""
        try:
            view = MerchandiseRegistrationView(self)
            view.show()
            self.open_views.append(view)
            if hasattr(self, 'activity_feed'):
                self.activity_feed.add_activity("merchandise", "Aberto cadastro de mercadoria")
        except Exception as e:
            self.show_error(f"Erro ao abrir cadastro de mercadoria: {e}")

    def open_carrier_registration(self):
        """Abre a tela de registro de transportadoras."""
        try:
            view = CarrierRegistrationView(self)
            view.show()
            self.open_views.append(view)
            if hasattr(self, 'activity_feed'):
                self.activity_feed.add_activity("carrier", "Aberto cadastro de transportadora")
        except Exception as e:
            self.show_error(f"Erro ao abrir cadastro de transportadora: {e}")

    def generate_report(self, report_type):
        """Gera relatório baseado no tipo."""
        if hasattr(self, 'activity_feed'):
            self.activity_feed.add_activity("export", f"Gerando relatório: {report_type}")
        self.show_success(f"Relatório '{report_type}' gerado com sucesso!")

    def logout(self):
        """Realiza logout do sistema."""
        reply = QMessageBox.question(self, "Confirmação", "Deseja realmente sair do sistema?",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.logout_signal.emit()
            self.close()

    def show_welcome_message(self):
        """Exibe mensagem de boas-vindas."""
        welcome_time = datetime.now().hour
        if welcome_time < 12:
            greeting = "Bom dia"
        elif welcome_time < 18:
            greeting = "Boa tarde"
        else:
            greeting = "Boa noite"
            
        welcome_msg = f"{greeting}, {self.usuario.get('nome_completo', 'Usuário')}! 👋"
        
        if hasattr(self, 'activity_feed'):
            self.activity_feed.add_activity("success", welcome_msg)

    def show_success(self, message):
        """Exibe mensagem de sucesso."""
        QMessageBox.information(self, "Sucesso", message)

    def show_error(self, message):
        """Exibe mensagem de erro."""
        QMessageBox.critical(self, "Erro", message)

    def show_safety_check_result(self, result):
        """Exibe resultado da consulta de segurança."""
        if isinstance(result, dict):
            # Formatar resultado como string
            result_text = f"""
🚗 **Resultado da Consulta de Segurança**

📋 **Placa:** {result.get('plate', 'N/A')}
✅ **Status:** {result.get('status', 'N/A')}
📊 **Nível de Risco:** {result.get('risk_level', 'N/A')}
💬 **Mensagem:** {result.get('message', 'N/A')}

⏰ **Consulta realizada em:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
            """.strip()
        else:
            result_text = str(result)
        
        # Exibir no widget de consulta
        if hasattr(self, 'vehicle_query_widget'):
            self.vehicle_query_widget.display_results(result_text)
        
        # Adicionar ao feed de atividades
        if hasattr(self, 'activity_feed'):
            self.activity_feed.add_activity("vehicle", f"Consulta realizada para placa: {result.get('plate', 'N/A')}")

    def update_access_logs(self, logs):
        """Atualiza a tabela de logs de acesso."""
        if hasattr(self, 'logs_table'):
            self.logs_table.setRowCount(len(logs))
            for row, log in enumerate(logs):
                for col, value in enumerate([log.get('plate', ''), log.get('type', ''), 
                                           log.get('driver', ''), log.get('timestamp', ''), 
                                           log.get('status', '')]):
                    item = QTableWidgetItem(str(value))
                    self.logs_table.setItem(row, col, item)

    def update_registered_vehicles(self, vehicles):
        """Atualiza a lista de veículos registrados."""
        # Implementar se necessário
        pass

    def update_metrics_panel(self, metrics):
        """Atualiza o painel de métricas."""
        # Implementar se necessário
        pass

    def toggle_fullscreen(self):
        """Alterna modo tela cheia."""
        if self.is_fullscreen:
            self.showNormal()
            self.is_fullscreen = False
        else:
            self.showFullScreen()
            self.is_fullscreen = True

    def show_about(self):
        """Exibe informações sobre o sistema."""
        QMessageBox.about(self, "Sobre o SENTRY", 
                         "SENTRY - Sistema de Controle Logístico\n\n"
                         "Versão 1.0\n"
                         "Sistema desenvolvido para gestão completa de operações logísticas.")

    def show_shortcuts(self):
        """Exibe atalhos de teclado."""
        QMessageBox.information(self, "Atalhos do Teclado",
                              "F5 - Atualizar dados\n"
                              "F11 - Tela cheia\n"
                              "Ctrl+Q - Sair\n"
                              "Ctrl+V - Registrar veículo\n"
                              "Ctrl+M - Registrar mercadoria\n"
                              "Ctrl+T - Registrar transportadora\n"
                              "Ctrl+E - Exportar dados")