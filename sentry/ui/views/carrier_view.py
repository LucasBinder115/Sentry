"""Carrier section view implementation."""

from PyQt5.QtWidgets import (
    QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QLineEdit, QLabel, QTabWidget,
    QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt

from .base_section_view import BaseSectionView
from .carrier_registration_view import CarrierRegistrationView
from ...data.database.carrier_repository import CarrierRepository
from ...core.export import DataExporter
from ...config import EXPORTS_DIR

class CarrierView(BaseSectionView):
    """Carrier management view with list and registration tabs."""

    def __init__(self, parent=None):
        """Initialize carrier view."""
        super().__init__("Gerenciamento de Transportadoras", parent)
        self.carrier_repo = CarrierRepository()
        self.exporter = DataExporter(EXPORTS_DIR)
        self.setup_content()
        self.load_carriers()
    
    def setup_content(self):
        """Setup the carrier view content."""
        layout = QVBoxLayout(self.content_area)

        # Tabs: Lista | Cadastro
        self.tabs = QTabWidget()

        # --- Tab 1: Lista ---
        list_container = QLabel()  # placeholder widget for layout holder
        list_layout = QVBoxLayout()

        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nome ou CNPJ...")
        self.search_input.textChanged.connect(self.load_carriers)
        search_layout.addWidget(self.search_input)

        add_btn = QPushButton("+ Nova Transportadora")
        add_btn.setFixedWidth(180)
        add_btn.clicked.connect(self._go_to_registration)
        search_layout.addWidget(add_btn)

        list_layout.addLayout(search_layout)

        # Carriers table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Nome", "CNPJ", "Telefone", "Status"])
        self.table.horizontalHeader().setStretchLastSection(True)
        list_layout.addWidget(self.table)

        # wrap list_layout into a QWidget
        from PyQt5.QtWidgets import QWidget
        list_page = QWidget()
        list_page.setLayout(list_layout)
        self.tabs.addTab(list_page, "Lista")

        # --- Tab 2: Cadastro ---
        self.registration_view = CarrierRegistrationView()
        self.registration_view.registration_successful.connect(self._handle_registration_success)
        self.registration_view.back_to_dashboard.connect(self._go_to_list)
        self.tabs.addTab(self.registration_view, "Cadastro")

        layout.addWidget(self.tabs)
    
    def load_carriers(self):
        """Load carriers into table."""
        try:
            # Get search filter
            search = self.search_input.text().strip()
            
            # Get carriers from repository
            carriers = self.carrier_repo.get_all()
            
            # Filter if search text exists
            if search:
                search = search.lower()
                carriers = [c for c in carriers if 
                          search in c['name'].lower() or
                          search in c['cnpj'].lower()]
            
            # Update table
            self.table.setRowCount(len(carriers))
            for row, carrier in enumerate(carriers):
                self.table.setItem(row, 0, QTableWidgetItem(carrier['name']))
                self.table.setItem(row, 1, QTableWidgetItem(carrier['cnpj']))
                self.table.setItem(row, 2, QTableWidgetItem(carrier.get('contact_phone', '')))
                self.table.setItem(row, 3, QTableWidgetItem(carrier['status']))
                
            # Adjust columns
            self.table.resizeColumnsToContents()
            
        except Exception as e:
            print(f"Error loading carriers: {e}")

    def _go_to_registration(self):
        """Switch to registration tab."""
        self.tabs.setCurrentIndex(1)

    def _go_to_list(self):
        """Switch to list tab."""
        self.tabs.setCurrentIndex(0)

    def _handle_registration_success(self, data: dict):
        """Persist new carrier and return to list."""
        try:
            saved = self.carrier_repo.create_carrier(
                name=data.get('name', ''),
                cnpj=data.get('cnpj', ''),
                contact_phone=data.get('phone')
            )
            QMessageBox.information(self, "Sucesso", "Transportadora cadastrada com sucesso!")
            self._go_to_list()
            self.load_carriers()
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao cadastrar transportadora: {e}")

    def export_data(self):
        """Export carriers to CSV using DataExporter."""
        try:
            carriers = self.carrier_repo.get_all()
            headers_map = {
                'name': 'Nome',
                'cnpj': 'CNPJ',
                'contact_phone': 'Telefone',
                'status': 'Status'
            }
            saved_path = self.exporter.export_to_csv(
                data=carriers,
                filename='transportadoras',
                headers=headers_map
            )
            QMessageBox.information(self, 'Sucesso', f'Dados exportados em:\n{saved_path}')
        except Exception as e:
            QMessageBox.warning(self, 'Erro', f'Erro ao exportar: {e}')