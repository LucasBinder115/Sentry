"""Home view implementation with statistics and quick access."""

from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QGridLayout, QScrollArea
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from ...data.database.vehicle_repository import VehicleRepository
from ...data.database.merchandise_repository import MerchandiseRepository
from ...data.database.carrier_repository import CarrierRepository
from ...data.database.access_log_repository import AccessLogRepository
from ...data.database.database_manager import DatabaseManager

class StatisticCard(QFrame):
    """Card widget to display statistics."""
    
    def __init__(self, title: str, value: str, icon: str, color: str = "#007bff"):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 8px;
                padding: 15px;
                border: 1px solid #dee2e6;
            }}
            QFrame:hover {{
                border-color: {color};
            }}
        """)
        
        layout = QVBoxLayout(self)
        
        # Icon and title
        header = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Arial", 24))
        header.addWidget(icon_label)
        header.addStretch()
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        header.addWidget(title_label)
        
        layout.addLayout(header)
        
        # Value
        value_label = QLabel(value)
        value_label.setFont(QFont("Arial", 24, QFont.Bold))
        value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_label)

class ActivityCard(QFrame):
    """Card widget to display recent activity."""
    
    def __init__(self, title: str, activities: list):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                padding: 15px;
                border: 1px solid #dee2e6;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title_label)
        
        # Activities list
        for activity in activities:
            activity_widget = QFrame()
            activity_widget.setStyleSheet("""
                QFrame {
                    border-bottom: 1px solid #dee2e6;
                    padding: 8px 0;
                }
            """)
            activity_layout = QVBoxLayout(activity_widget)
            activity_layout.setContentsMargins(0, 0, 0, 0)
            
            desc_label = QLabel(activity['description'])
            desc_label.setWordWrap(True)
            activity_layout.addWidget(desc_label)
            
            # 💡 CORREÇÃO AQUI: Convertendo datetime.datetime para string
            time_value = activity['time']
            if isinstance(time_value, datetime):
                # Formato sugerido: DD/MM/YYYY HH:MM:SS
                time_string = time_value.strftime("%d/%m/%Y %H:%M:%S")
            else:
                # Caso não seja datetime (já deveria ser string ou algo que aceite str())
                time_string = str(time_value)
                
            time_label = QLabel(time_string)
            time_label.setStyleSheet("color: #6c757d; font-size: 10px;")
            activity_layout.addWidget(time_label)
            
            layout.addWidget(activity_widget)

class HomeView(QWidget):
    """Home view with statistics and recent activity."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.vehicle_repo = VehicleRepository()
        self.merchandise_repo = MerchandiseRepository()
        self.carrier_repo = CarrierRepository()
        self.access_repo = AccessLogRepository()
        self.db = DatabaseManager()
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the home view UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Welcome section
        welcome = QLabel("Dashboard")
        welcome.setFont(QFont("Arial", 24, QFont.Bold))
        layout.addWidget(welcome)
        
        date_label = QLabel(datetime.now().strftime("%d de %B de %Y"))
        date_label.setStyleSheet("color: #6c757d;")
        layout.addWidget(date_label)
        
        # Statistics grid
        stats_grid = QGridLayout()
        stats_grid.setSpacing(15)
        
        # Get statistics
        stats = self.get_statistics()
        
        # Create statistic cards
        stats_grid.addWidget(StatisticCard(
            "Veículos Ativos", 
            str(stats['active_vehicles']),
            "🚛",
            "#28a745"
        ), 0, 0)
        
        stats_grid.addWidget(StatisticCard(
            "Mercadorias", 
            str(stats['total_merchandise']),
            "📦",
            "#007bff"
        ), 0, 1)
        
        stats_grid.addWidget(StatisticCard(
            "Transportadoras", 
            str(stats['total_carriers']),
            "🏢",
            "#17a2b8"
        ), 0, 2)
        
        stats_grid.addWidget(StatisticCard(
            "Registros Hoje", 
            str(stats['today_logs']),
            "📝",
            "#dc3545"
        ), 0, 3)

        # New status cards row
        latest_summary = self.get_latest_scan_summary()
        stats_grid.addWidget(StatisticCard(
            "Último OCR",
            latest_summary,
            "📸",
            "#6f42c1"
        ), 1, 0)

        failed_today = self.get_failed_attempts_today()
        stats_grid.addWidget(StatisticCard(
            "Falhas OCR (hoje)",
            str(failed_today),
            "❌",
            "#e83e8c"
        ), 1, 1)
        
        layout.addLayout(stats_grid)
        
        # Two-column: left recent lists, right activity timeline
        row = QHBoxLayout()

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.NoFrame)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        recent_vehicles = ActivityCard(
            "Veículos Recentes",
            self.get_recent_vehicles()
        )
        left_layout.addWidget(recent_vehicles)

        recent_merchandise = ActivityCard(
            "Movimentações Recentes",
            self.get_recent_merchandise()
        )
        left_layout.addWidget(recent_merchandise)

        left_scroll.setWidget(left_widget)
        row.addWidget(left_scroll, 2)

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.NoFrame)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        timeline = ActivityCard(
            "Atividade do Sistema",
            self.get_recent_activities()
        )
        right_layout.addWidget(timeline)

        right_scroll.setWidget(right_widget)
        row.addWidget(right_scroll, 1)

        layout.addLayout(row)
        
    def get_statistics(self) -> dict:
        """Get current statistics."""
        try:
            return {
                'active_vehicles': len([v for v in self.vehicle_repo.get_all() if v['status'] == 'ACTIVE']),
                'total_merchandise': len(self.merchandise_repo.get_all()),
                'total_carriers': len(self.carrier_repo.get_all() if hasattr(self.carrier_repo, 'get_all') else []),
                'today_logs': len(self.access_repo.get_today_logs())
            }
        except Exception:
            return {
                'active_vehicles': 0,
                'total_merchandise': 0,
                'total_carriers': 0,
                'today_logs': 0
            }
    
    def get_recent_vehicles(self) -> list:
        """Get recent vehicle activity."""
        try:
            vehicles = self.vehicle_repo.get_recent_vehicles(5)
            return [
                {
                    'description': f"Veículo {v['plate']} - {v['model']}",
                    'time': v['created_at']
                }
                for v in vehicles
            ]
        except Exception:
            return []
    
    def get_recent_merchandise(self) -> list:
        """Get recent merchandise activity."""
        try:
            items = self.merchandise_repo.get_recent_items(5)
            return [
                {
                    'description': f"{i['name']} - {i['quantity']} {i['unit']}",
                    'time': i['updated_at']
                }
                for i in items
            ]
        except Exception:
            return []
    
    def get_recent_activities(self) -> list:
        """Get recent activity logs for timeline."""
        try:
            rows = self.db.get_recent_activities(20)
            return [
                {
                    'description': f"{r['activity_type']}: {r['description']}",
                    'time': r['created_at']
                }
                for r in rows
            ]
        except Exception:
            return []

    def get_latest_scan_summary(self) -> str:
        """Return latest OCR/access summary string for card."""
        try:
            latest = self.access_repo.get_latest_scan()
            if not latest:
                return "—"
            plate = latest.get('plate') or latest.get('detected_plate') or '—'
            ts = latest.get('created_at') or latest.get('timestamp') or ''
            return f"{plate}\n{ts}"
        except Exception:
            return "—"

    def get_failed_attempts_today(self) -> int:
        """Return count of today's failed OCR (UNAUTHORIZED)."""
        try:
            return self.access_repo.count_today_failed_attempts()
        except Exception:
            return 0