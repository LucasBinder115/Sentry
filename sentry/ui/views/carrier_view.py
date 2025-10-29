"""Carrier section view implementation."""

from PyQt5.QtWidgets import (
    QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QLineEdit, QLabel
)
from PyQt5.QtCore import Qt

from .base_section_view import BaseSectionView
from ...data.database.carrier_repository import CarrierRepository

class CarrierView(BaseSectionView):
    """Carrier management view."""
    
    def __init__(self, parent=None):
        """Initialize carrier view."""
        super().__init__("Gerenciamento de Transportadoras", parent)
        self.carrier_repo = CarrierRepository()
        self.setup_content()
        self.load_carriers()
    
    def setup_content(self):
        """Setup the carrier view content."""
        layout = QVBoxLayout(self.content_area)
        
        # Search bar
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nome ou CNPJ...")
        self.search_input.textChanged.connect(self.load_carriers)
        search_layout.addWidget(self.search_input)
        
        # Add carrier button
        add_btn = QPushButton("+ Nova Transportadora")
        add_btn.setFixedWidth(180)
        search_layout.addWidget(add_btn)
        
        layout.addLayout(search_layout)
        
        # Carriers table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Nome", "CNPJ", "Telefone", "Status"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
    
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