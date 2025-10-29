"""Dashboard view implementation with organized top navigation and OCR integration."""

from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QStackedWidget, QTabBar, QSizePolicy,
    QMessageBox
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont

from .vehicles_view import VehiclesView
from .merchandise_view import MerchandiseView
from .carrier_view import CarrierView
from .ocr_camera_view import OCRCameraView
from ...data.database.vehicle_repository import VehicleRepository
from ...data.database.access_log_repository import AccessLogRepository


class DashboardView(QWidget):
    """Modern dashboard with top navigation and stacked content."""

    logout = pyqtSignal()

    def __init__(self, user_data: dict):
        super().__init__()
        self.user_data = user_data or {}
        self.vehicle_repo = VehicleRepository()
        self.access_repo = AccessLogRepository()

        self.setWindowTitle("SENTRY - Dashboard")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top bar
        top_bar = QFrame()
        top_bar.setFixedHeight(60)
        top_bar.setStyleSheet("background-color: #ffffff; border-bottom: 1px solid #dee2e6;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 0, 20, 0)

        logo = QLabel("SENTRY")
        logo.setFont(QFont("Arial", 18, QFont.Bold))
        top_layout.addWidget(logo)
        top_layout.addStretch()

        user_label = QLabel(f"Bem-vindo, {self.user_data.get('username', 'Usuário')}")
        user_label.setFont(QFont("Arial", 12))
        top_layout.addWidget(user_label)

        logout_btn = QPushButton("Sair")
        logout_btn.setFixedWidth(100)
        logout_btn.clicked.connect(self.logout.emit)
        top_layout.addWidget(logout_btn)

        layout.addWidget(top_bar)

        # Navigation bar with tabs and quick actions
        nav_frame = QFrame()
        nav_frame.setStyleSheet("background-color: #ffffff;")
        nav_layout = QHBoxLayout(nav_frame)
        nav_layout.setContentsMargins(20, 8, 20, 8)

        self.tab_bar = QTabBar()
        self.tab_bar.setDrawBase(False)
        self.tab_bar.addTab("🚛 Veículos")
        self.tab_bar.addTab("📦 Mercadorias")
        self.tab_bar.addTab("🏢 Transportadoras")
        self.tab_bar.addTab("📸 OCR Camera")
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        nav_layout.addWidget(self.tab_bar)

        nav_layout.addStretch()

        scan_btn = QPushButton("🔍 Scan Rápido")
        scan_btn.setStyleSheet("background-color: #28a745; color: white; border: none; padding: 8px 16px; border-radius: 4px;")
        scan_btn.clicked.connect(self._quick_scan)
        nav_layout.addWidget(scan_btn)

        export_btn = QPushButton("📊 Exportar Dados")
        export_btn.setStyleSheet("background-color: #17a2b8; color: white; border: none; padding: 8px 16px; border-radius: 4px;")
        export_btn.clicked.connect(self._export_data)
        nav_layout.addWidget(export_btn)

        layout.addWidget(nav_frame)

        # Stacked content area
        self.stack = QStackedWidget()
        self.vehicles_view = VehiclesView(self)
        self.merchandise_view = MerchandiseView(self)
        self.carrier_view = CarrierView(self)
        self.ocr_view = OCRCameraView(self)

        # connect OCR detection
        try:
            self.ocr_view.plate_detected.connect(self._handle_plate_detection)
        except Exception:
            pass

        self.stack.addWidget(self.vehicles_view)
        self.stack.addWidget(self.merchandise_view)
        self.stack.addWidget(self.carrier_view)
        self.stack.addWidget(self.ocr_view)

        layout.addWidget(self.stack)

    def _on_tab_changed(self, index: int):
        self.stack.setCurrentIndex(index)

    def _quick_scan(self):
        # switch to OCR tab and start camera
        self.tab_bar.setCurrentIndex(3)
        try:
            self.ocr_view.start_camera()
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível iniciar câmera: {e}")

    def _export_data(self):
        current = self.stack.currentWidget()
        if hasattr(current, 'export_data'):
            try:
                current.export_data()
            except Exception as e:
                QMessageBox.warning(self, "Erro", f"Erro ao exportar dados: {e}")
        else:
            QMessageBox.information(self, "Exportar", "Esta seção não oferece exportação.")

    def _handle_plate_detection(self, plate: str):
        # basic handling: lookup vehicle and log access
        try:
            vehicle = self.vehicle_repo.get_by_plate(plate)
            if vehicle:
                self.access_repo.create({
                    'vehicle_id': vehicle.get('id'),
                    'timestamp': datetime.now(),
                    'detected_plate': plate,
                    'status': 'AUTHORIZED'
                })
                # show brief info on OCR view
                self.ocr_view.last_detection.setText(f"✅ Veículo autorizado: {plate}\nModelo: {vehicle.get('model')} | Status: {vehicle.get('status')}")
            else:
                self.access_repo.create({
                    'vehicle_id': None,
                    'timestamp': datetime.now(),
                    'detected_plate': plate,
                    'status': 'UNAUTHORIZED'
                })
                self.ocr_view.last_detection.setText(f"❌ Veículo não autorizado: {plate}")
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao processar placa: {e}")
