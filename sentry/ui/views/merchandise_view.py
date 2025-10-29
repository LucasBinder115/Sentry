"""Merchandise section view implementation."""

from PyQt5.QtWidgets import (
    QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QLineEdit, QLabel,
    QComboBox
)
from PyQt5.QtCore import Qt

from .base_section_view import BaseSectionView

class MerchandiseView(BaseSectionView):
    """Merchandise management view."""
    
    def __init__(self, parent=None):
        """Initialize merchandise view."""
        super().__init__("Controle de Mercadorias", parent)
        self.setup_content()
        self.load_demo_data()  # TODO: Replace with real data
    
    def setup_content(self):
        """Setup the merchandise view content."""
        layout = QVBoxLayout(self.content_area)
        
        # Filters bar
        filters_layout = QHBoxLayout()
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar mercadoria...")
        filters_layout.addWidget(self.search_input)
        
        # Status filter
        self.status_filter = QComboBox()
        self.status_filter.addItems(["Todos", "Em Estoque", "Em Trânsito", "Entregue"])
        filters_layout.addWidget(QLabel("Status:"))
        filters_layout.addWidget(self.status_filter)
        
        # Add merchandise button
        add_btn = QPushButton("+ Nova Mercadoria")
        add_btn.setFixedWidth(150)
        filters_layout.addWidget(add_btn)
        
        layout.addLayout(filters_layout)
        
        # Merchandise table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Código", "Descrição", "Quantidade", "Status", "Última Atualização"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
    
    def load_demo_data(self):
        """Load demo data into table."""
        # Demo data
        items = [
            ("M001", "Caixa Grande", "50", "Em Estoque", "29/10/2025"),
            ("M002", "Pacote Médio", "30", "Em Trânsito", "29/10/2025"),
            ("M003", "Container A", "10", "Em Estoque", "29/10/2025"),
            ("M004", "Pallet B", "25", "Entregue", "28/10/2025"),
        ]
        
        # Update table
        self.table.setRowCount(len(items))
        for row, item in enumerate(items):
            for col, value in enumerate(item):
                self.table.setItem(row, col, QTableWidgetItem(value))
        
        # Adjust columns
        self.table.resizeColumnsToContents()