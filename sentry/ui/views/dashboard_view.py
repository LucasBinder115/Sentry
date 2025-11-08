"""Dashboard view implementation with organized top navigation and OCR integration."""

from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QStackedWidget, QTabBar, QSizePolicy,
    QMessageBox, QLineEdit, QMenu, QFileDialog
)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont

from .vehicles_view import VehiclesView
from .merchandise_view import MerchandiseView
from .carrier_view import CarrierView
from .ocr_camera_view import OCRCameraView
from .analytics_view import AnalyticsView
from .home_view import HomeView
from .logs_view import LogsView
from ...data.database.vehicle_repository import VehicleRepository
from ...data.database.merchandise_repository import MerchandiseRepository
from ...data.database.carrier_repository import CarrierRepository
from ...data.database.access_log_repository import AccessLogRepository
from ...data.database.database_manager import DatabaseManager
from ...data.database.backup_manager import BackupManager
from ...core.plugin_manager import PluginManager
from ...core.event_bus import get_event_bus
from ...core.task_queue import get_task_queue
from ... import config
from ...core.config_loader import ConfigLoader
from ...core.ocr import set_ocr_engine, set_preprocessing, set_confidence_threshold, set_tesseract_cmd


class DashboardView(QWidget):
    """Modern dashboard with top navigation and stacked content."""

    logout = pyqtSignal()

    def __init__(self, user_data: dict):
        super().__init__()
        self.user_data = user_data or {}
        self.dark_mode = False
        
        # Initialize repositories
        self.vehicle_repo = VehicleRepository()
        self.merchandise_repo = MerchandiseRepository()
        self.carrier_repo = CarrierRepository()
        self.access_repo = AccessLogRepository()
        
        self.setWindowTitle("SENTRY - Dashboard")
        # Load configuration
        try:
            self.cfg = ConfigLoader(config.CONFIG_DIR).load()
        except Exception:
            self.cfg = {}
        self._setup_ui()
        
        # Start on home view
        self.tab_bar.setCurrentIndex(0)

        # Initialize daily backup scheduler
        try:
            self._init_backup_scheduler()
        except Exception:
            pass

        # Initialize plugin system
        try:
            self._plugins = PluginManager(config.PLUGINS_DIR)
            enabled = (self.cfg.get('plugins') or {}).get('enabled') if isinstance(self.cfg.get('plugins'), dict) else None
            if enabled and isinstance(enabled, list) and len(enabled) > 0:
                for name in enabled:
                    try:
                        self._plugins.load(str(name))
                    except Exception:
                        pass
            else:
                self._plugins.load_all()
        except Exception:
            self._plugins = None

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
        self.tab_bar.addTab("🏠 Início")
        self.tab_bar.addTab("🚛 Veículos")
        self.tab_bar.addTab("📦 Mercadorias")
        self.tab_bar.addTab("🏢 Transportadoras")
        self.tab_bar.addTab("📸 OCR Camera")
        self.tab_bar.addTab("📈 Analytics")
        self.tab_bar.addTab("🪵 Logs")
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        nav_layout.addWidget(self.tab_bar)

        nav_layout.addStretch()

        # Unified search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Pesquisar veículos, mercadorias, transportadoras...")
        self.search_input.setFixedWidth(360)
        self.search_input.returnPressed.connect(self._perform_search)
        nav_layout.addWidget(self.search_input)

        # Theme toggle
        self.theme_btn = QPushButton("🌙")
        self.theme_btn.setFixedWidth(44)
        self.theme_btn.clicked.connect(self._toggle_theme)
        nav_layout.addWidget(self.theme_btn)

        # Notifications button
        self.notify_btn = QPushButton("🔔")
        self.notify_btn.setFixedWidth(44)
        self.notify_btn.clicked.connect(self._show_notifications)
        nav_layout.addWidget(self.notify_btn)

        scan_btn = QPushButton("🔍 Scan Rápido")
        scan_btn.setStyleSheet("background-color: #28a745; color: white; border: none; padding: 8px 16px; border-radius: 4px;")
        scan_btn.clicked.connect(self._quick_scan)
        nav_layout.addWidget(scan_btn)

        export_btn = QPushButton("📊 Exportar Dados")
        export_btn.setStyleSheet("background-color: #17a2b8; color: white; border: none; padding: 8px 16px; border-radius: 4px;")
        export_btn.clicked.connect(self._export_data)
        nav_layout.addWidget(export_btn)

        layout.addWidget(nav_frame)

        # Initialize database manager
        self.db = DatabaseManager()
        
        # Stacked content area
        self.stack = QStackedWidget()
        
        # Add all views
        self.home_view = HomeView(self)
        self.vehicles_view = VehiclesView(self)
        self.merchandise_view = MerchandiseView(self)
        self.carrier_view = CarrierView(self)
        self.ocr_view = OCRCameraView(self)
        self.analytics_view = AnalyticsView(self)
        self.logs_view = LogsView(self)
        
        # Add views to stack
        self.stack.addWidget(self.home_view)
        self.stack.addWidget(self.vehicles_view)
        self.stack.addWidget(self.merchandise_view)
        self.stack.addWidget(self.carrier_view)
        self.stack.addWidget(self.ocr_view)
        self.stack.addWidget(self.analytics_view)
        self.stack.addWidget(self.logs_view)
        
        layout.addWidget(self.stack)
        
        # connect OCR detection
        try:
            self.ocr_view.plate_detected.connect(self._handle_plate_detection)
        except Exception:
            pass

        # Also log that dashboard started
        try:
            self.db.log_activity('SESSION', 'Dashboard started', 'system')
        except Exception:
            pass
        # Publish app_started event
        try:
            get_event_bus().publish('app.started', {'user': self.user_data})
        except Exception:
            pass

        # Apply OCR config and camera source
        try:
            ocr_cfg = self.cfg.get('ocr') or {}
            if isinstance(ocr_cfg, dict):
                if ocr_cfg.get('engine'):
                    set_ocr_engine(str(ocr_cfg.get('engine')))
                if ocr_cfg.get('tesseract_cmd'):
                    try:
                        set_tesseract_cmd(str(ocr_cfg.get('tesseract_cmd')))
                    except Exception:
                        pass
                if 'confidence_threshold' in ocr_cfg:
                    set_confidence_threshold(float(ocr_cfg.get('confidence_threshold') or 0.6))
                if 'preprocessing' in ocr_cfg:
                    set_preprocessing(bool(ocr_cfg.get('preprocessing')))
        except Exception:
            pass
        try:
            cam_cfg = (self.cfg.get('cameras') or [])
            if isinstance(cam_cfg, list) and len(cam_cfg) > 0:
                source = cam_cfg[0].get('source')
                if source is not None:
                    self.ocr_view.preferred_source = source
        except Exception:
            pass

    def _on_tab_changed(self, index: int):
        """Handle tab changes and view refreshes."""
        # Set the current view
        self.stack.setCurrentIndex(index)
        
        # Refresh current view if it has a refresh method
        current = self.stack.currentWidget()
        if hasattr(current, 'refresh'):
            try:
                current.refresh()
            except Exception as e:
                self.logger.error(f"Error refreshing view: {e}")
        
        # Handle special cases
        if index == 4:  # OCR Camera
            try:
                self.ocr_view.start_camera()
            except Exception as e:
                QMessageBox.warning(self, "Erro", f"Não foi possível iniciar câmera: {e}")
        else:
            # Stop camera if we're leaving the OCR view
            try:
                self.ocr_view.stop_camera()
            except Exception:
                pass

    def _quick_scan(self):
        # switch to OCR tab and start camera
        self.tab_bar.setCurrentIndex(4)
        try:
            self.ocr_view.start_camera()
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível iniciar câmera: {e}")

    def _export_data(self):
        """Export data from current view."""
        current = self.stack.currentWidget()
        if hasattr(current, 'export_data'):
            try:
                # Audit: export initiated
                try:
                    self.db.log_activity('EXPORT', f'Export from view {type(current).__name__}', type(current).__name__)
                except Exception:
                    pass
                current.export_data()
                try:
                    get_event_bus().publish('export.completed', {'view': type(current).__name__})
                except Exception:
                    pass
            except Exception as e:
                QMessageBox.warning(self, "Erro", f"Erro ao exportar dados: {e}")
        else:
            # Create an export menu if multiple exports are available
            from PyQt5.QtWidgets import QMenu
            
            menu = QMenu(self)
            
            # Add export options
            vehicles_action = menu.addAction("🚛 Exportar Veículos")
            vehicles_action.triggered.connect(self.vehicles_view.export_data)
            
            merch_action = menu.addAction("📦 Exportar Mercadorias")
            merch_action.triggered.connect(self.merchandise_view.export_data)
            
            carriers_action = menu.addAction("🏢 Exportar Transportadoras")
            carriers_action.triggered.connect(self.carrier_view.export_data)
            
            # Add separator and special exports
            menu.addSeparator()
            
            activity_action = menu.addAction("📝 Exportar Registros de Atividade")
            activity_action.triggered.connect(self._export_activity_logs)
            
            # Show menu under export button
            button = self.sender()
            menu.exec_(button.mapToGlobal(button.rect().bottomLeft()))
            QMessageBox.information(self, "Exportar", "Esta seção não oferece exportação.")

    def _export_activity_logs(self):
        """Open a save dialog and export recent activity logs in selected format."""
        try:
            # Fetch data
            try:
                rows = self.db.get_recent_activities(limit=500) or []
                # rows are sqlite3.Row; convert to dicts
                records = [dict(r) for r in rows]
            except Exception:
                records = []

            if not records:
                QMessageBox.information(self, "Exportar", "Sem registros de atividade para exportar.")
                return

            # Choose file and format
            filters = "PDF (*.pdf);;CSV (*.csv);;Word (*.docx)"
            path, sel_filter = QFileDialog.getSaveFileName(self, "Exportar Registros de Atividade", "", filters)
            if not path:
                return

            fmt = None
            low = path.lower()
            if sel_filter.startswith("PDF") or low.endswith(".pdf"):
                fmt = 'pdf'
                if not low.endswith('.pdf'):
                    path += ".pdf"
            elif sel_filter.startswith("CSV") or low.endswith(".csv"):
                fmt = 'csv'
                if not low.endswith('.csv'):
                    path += ".csv"
            elif sel_filter.startswith("Word") or low.endswith(".docx"):
                fmt = 'docx'
                if not low.endswith('.docx'):
                    path += ".docx"
            else:
                # default to CSV
                fmt = 'csv'
                if not low.endswith('.csv'):
                    path += ".csv"

            # Lazy import exporters
            try:
                from ...core.export_manager import (
                    export_to_pdf, export_to_csv, export_to_docx, get_dependency_status
                )
            except Exception as e:
                QMessageBox.warning(self, "Exportar", f"Falha ao carregar exportadores: {e}")
                return

            deps = get_dependency_status()
            title = "Registros de Atividade"

            try:
                if fmt == 'pdf':
                    if not deps.get('pdf'):
                        QMessageBox.warning(self, "Exportar", "Biblioteca ReportLab não instalada.")
                        return
                    export_to_pdf(path, title, records)
                elif fmt == 'csv':
                    if not deps.get('csv'):
                        QMessageBox.warning(self, "Exportar", "Biblioteca pandas não instalada.")
                        return
                    export_to_csv(path, records)
                elif fmt == 'docx':
                    if not deps.get('docx'):
                        QMessageBox.warning(self, "Exportar", "Biblioteca python-docx não instalada.")
                        return
                    export_to_docx(path, title, records)
                else:
                    QMessageBox.warning(self, "Exportar", "Formato de exportação não suportado.")
                    return
            except Exception as e:
                QMessageBox.warning(self, "Exportar", f"Erro ao exportar: {e}")
                return

            QMessageBox.information(self, "Exportar", f"Exportação concluída: {path}")
        except Exception as e:
            QMessageBox.warning(self, "Exportar", f"Falha na exportação: {e}")

    def _handle_plate_detection(self, plate: str):
        # basic handling: lookup vehicle and log access; prompt minimal actions on vehicles
        try:
            # Duplicate detection within 60 seconds
            try:
                if self.access_repo.is_duplicate_scan(plate, window_seconds=60):
                    try:
                        self.db.log_activity('ALERT', f'Duplicate scan detected for {plate}', 'access_logs')
                    except Exception:
                        pass
                    QMessageBox.information(self, 'Alerta', f'Leitura duplicada detectada para {plate} (últimos 60s).')
            except Exception:
                pass

            vehicle = self.vehicle_repo.get_by_plate(plate)
            # Selected carrier from OCR tab (simple linkage)
            try:
                carrier_id = self.ocr_view.get_selected_carrier_id()
            except Exception:
                carrier_id = None
            if vehicle:
                self.access_repo.create(
                    vehicle_id=vehicle.get('id'),
                    detected_plate=plate,
                    status='AUTHORIZED',
                    carrier_id=carrier_id
                )
                # show brief info on OCR view
                self.ocr_view.last_detection.setText(f"✅ Veículo autorizado: {plate}\nModelo: {vehicle.get('model')} | Status: {vehicle.get('status')}")
                try:
                    self.db.log_activity('ACCESS', f'Authorized access {plate}', 'access_logs')
                except Exception:
                    pass
                try:
                    get_event_bus().publish('ocr.scan_completed', {
                        'plate': plate,
                        'authorized': True,
                        'vehicle': vehicle
                    })
                except Exception:
                    pass
                # Prompt: open vehicle details?
                reply = QMessageBox.question(
                    self,
                    "Veículo Detectado",
                    f"Placa {plate} reconhecida. Deseja abrir os detalhes do veículo?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    # switch to Vehicles tab and open edit dialog for this plate
                    self.tab_bar.setCurrentIndex(1)
                    try:
                        table = self.vehicles_view.table
                        # find row with plate
                        target_row = None
                        for r in range(table.rowCount()):
                            item = table.item(r, 0)
                            if item and item.text().strip().upper() == plate.strip().upper():
                                target_row = r
                                break
                        if target_row is not None:
                            index = table.model().index(target_row, 0)
                            self.vehicles_view.edit_vehicle(index)
                    except Exception:
                        pass
            else:
                self.access_repo.create(
                    vehicle_id=None,
                    detected_plate=plate,
                    status='UNAUTHORIZED',
                    carrier_id=carrier_id
                )
                self.ocr_view.last_detection.setText(f"❌ Veículo não autorizado: {plate}")
                try:
                    self.db.log_activity('ACCESS', f'Unauthorized access {plate}', 'access_logs')
                except Exception:
                    pass
                try:
                    get_event_bus().publish('ocr.scan_completed', {
                        'plate': plate,
                        'authorized': False
                    })
                except Exception:
                    pass
                # Prompt: register new vehicle?
                reply = QMessageBox.question(
                    self,
                    "Veículo Não Encontrado",
                    f"Placa {plate} não cadastrada. Deseja registrar agora?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.tab_bar.setCurrentIndex(1)
                    try:
                        self.vehicles_view.add_vehicle()
                    except Exception:
                        pass
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao processar placa: {e}")

    # --- Backup scheduling ---
    def _init_backup_scheduler(self):
        """Schedule a daily backup using QTimer and BackupManager."""
        self._backup_manager = BackupManager()
        self._backup_timer = QTimer(self)
        self._backup_timer.setSingleShot(True)
        self._backup_timer.timeout.connect(self._run_daily_backup)
        self._schedule_next_backup()

    def _schedule_next_backup(self):
        """Schedule next backup at 03:00 local time (or 60s from now if missed)."""
        try:
            now = datetime.now()
            backup_hour = 3
            try:
                bcfg = self.cfg.get('backups') or {}
                if isinstance(bcfg, dict) and ('hour' in bcfg):
                    backup_hour = int(bcfg.get('hour') or 3)
            except Exception:
                backup_hour = 3
            target = now.replace(hour=backup_hour, minute=0, second=0, microsecond=0)
            if target <= now:
                from datetime import timedelta
                target = target + timedelta(days=1)
            msecs = int((target - now).total_seconds() * 1000)
            # Safety: if computed negative/zero, run in 60s
            if msecs <= 0:
                msecs = 60 * 1000
            self._backup_timer.start(msecs)
        except Exception:
            # Fallback: run in 5 minutes
            self._backup_timer.start(5 * 60 * 1000)

    def _run_daily_backup(self):
        """Execute backup and reschedule for the next day."""
        def _job():
            ok_local = False
            try:
                ok_local = bool(self._backup_manager.create_backup(self.db.db_path, description='Scheduled daily backup'))
                try:
                    self.db.log_activity('BACKUP', f'Daily backup {"ok" if ok_local else "failed"}', 'system')
                except Exception:
                    pass
                try:
                    get_event_bus().publish('backup.completed', {'ok': ok_local})
                except Exception:
                    pass
                # Retention cleanup
                try:
                    bcfg = self.cfg.get('backups') or {}
                    retention = int(bcfg.get('retention') or 0) if isinstance(bcfg, dict) else 0
                    if retention > 0:
                        from ...data.database.backup_manager import BackupManager as _BM
                        _BM().cleanup_old_backups(max_backups=retention)
                except Exception:
                    pass
            except Exception:
                pass
            finally:
                # After running, schedule next in 24h
                self._backup_timer.setSingleShot(True)
                self._backup_timer.start(24 * 60 * 60 * 1000)
        try:
            get_task_queue().submit(_job)
        except Exception:
            _job()

    def _perform_search(self):
        """Unified search across main entities."""
        term = (self.search_input.text() or "").strip()
        if not term:
            return
        try:
            # Try vehicles first (by plate/model)
            v_rows = self.vehicle_repo.search(plate=term, model=term)
            if v_rows:
                self.tab_bar.setCurrentIndex(1)
                try:
                    self.vehicles_view.search_input.setText(term)
                    self.vehicles_view.load_vehicles()
                except Exception:
                    pass
                return
            # Merchandise
            m_rows = self.merchandise_repo.search(name=term, description=term)
            if m_rows:
                self.tab_bar.setCurrentIndex(2)
                try:
                    self.merchandise_view.search_input.setText(term)
                    self.merchandise_view.load_merchandise()
                except Exception:
                    pass
                return
            # Carriers
            c_rows = self.carrier_repo.search(name=term, cnpj=term)
            if c_rows:
                self.tab_bar.setCurrentIndex(3)
                try:
                    self.carrier_view.search_input.setText(term)
                    self.carrier_view.load_carriers()
                except Exception:
                    pass
                return
            QMessageBox.information(self, "Pesquisa", "Nenhum resultado encontrado.")
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Falha na pesquisa: {e}")

    def _toggle_theme(self):
        """Toggle between light and dark theme for the app."""
        try:
            self.dark_mode = not self.dark_mode
            app = self.window().windowHandle()
            # Apply a simple stylesheet switch on the widget tree
            palette = (
                """
                QWidget { background-color: #121212; color: #e9ecef; }
                QFrame { background-color: #1e1e1e; border: 1px solid #2a2a2a; }
                QLineEdit { background:#1e1e1e; color:#e9ecef; border:1px solid #2a2a2a; }
                QPushButton { background:#2a2a2a; color:#e9ecef; border:none; padding:6px 10px; border-radius:4px; }
                QTabBar::tab { background:#2a2a2a; color:#e9ecef; }
                QTabBar::tab:selected { background:#28a745; color:#fff; }
                """
                if self.dark_mode else
                """
                QWidget { background-color: #f8f9fa; color: #2c3e50; }
                QFrame { background-color: #ffffff; border: 1px solid #dee2e6; }
                QLineEdit { background:#ffffff; color:#2c3e50; border:1px solid #dee2e6; }
                QPushButton { background:#ffffff; color:#2c3e50; border:1px solid #dee2e6; padding:6px 10px; border-radius:4px; }
                QTabBar::tab { background:#f1f3f5; color:#2c3e50; }
                QTabBar::tab:selected { background:#28a745; color:#fff; }
                """
            )
            self.setStyleSheet(palette)
            self.theme_btn.setText("☀️" if self.dark_mode else "🌙")
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível alternar o tema: {e}")

    def _show_notifications(self):
        """Show notifications menu with OCR alerts."""
        try:
            menu = QMenu(self)
            # Today's failed OCR attempts
            try:
                failed = self.access_repo.count_today_failed_attempts()
            except Exception:
                failed = 0
            act_failed = menu.addAction(f"Falhas de OCR hoje: {failed}")
            act_failed.setEnabled(False)

            # Latest unauthorized attempt
            try:
                logs = self.access_repo.get_recent_logs(10)
                last_unauth = next((l for l in logs if l.get('status') == 'UNAUTHORIZED'), None)
                if last_unauth:
                    plate = last_unauth.get('plate') or last_unauth.get('detected_plate')
                    menu.addAction(f"Última falha: {plate}")
            except Exception:
                pass

            # Alerts: camera offline and high failure rate (15 min)
            try:
                # thresholds from config with defaults
                alerts_cfg = (self.cfg.get('alerts') or {}) if isinstance(self.cfg.get('alerts'), dict) else {}
                camera_secs = int(alerts_cfg.get('camera_offline_seconds') or 30)
                fail_rate_thresh = float(alerts_cfg.get('high_failure_rate') or 0.3)
                offline_sec = self.ocr_view.camera_offline_seconds()
                if offline_sec is not None and offline_sec >= camera_secs:
                    menu.addAction(f"⚠️ Câmera offline: {offline_sec}s")
                rate = self.access_repo.get_failure_rate_minutes(15)
                if rate >= fail_rate_thresh:
                    menu.addAction(f"⚠️ Taxa falhas 15min: {rate*100:.0f}%")
            except Exception:
                pass

            # Generic entries
            menu.addSeparator()
            menu.addAction("Abrir Registros", lambda: self.tab_bar.setCurrentIndex(0))

            button = self.sender()
            menu.exec_(button.mapToGlobal(button.rect().bottomLeft()))
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Falha ao abrir notificações: {e}")
