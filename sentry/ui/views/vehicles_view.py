"""Vehicle section view implementation."""

from PyQt5.QtWidgets import (
    QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QLineEdit, QLabel,
    QMenu, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt

from .base_section_view import BaseSectionView
from ..widgets.vehicle_form_dialog import VehicleFormDialog
from ...data.database.vehicle_repository import VehicleRepository
from ...core.export import DataExporter
from ...config import EXPORTS_DIR

class VehiclesView(BaseSectionView):
    """Vehicle management view."""
    
    def __init__(self, parent=None):
        """Initialize vehicles view."""
        super().__init__("Gerenciamento de Veículos", parent)
        self.vehicle_repo = VehicleRepository()
        self.exporter = DataExporter(EXPORTS_DIR)
        self.setup_content()
        self.load_vehicles()
    
    def setup_content(self):
        """Setup the vehicles view content."""
        layout = QVBoxLayout(self.content_area)
        
        # Search bar
        search_layout = QHBoxLayout()
        
        # Search input with icon label
        search_container = QHBoxLayout()
        search_container.setSpacing(5)
        
        search_icon = QLabel("🔍")
        search_container.addWidget(search_icon)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por placa...")
        self.search_input.textChanged.connect(self.load_vehicles)
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #80bdff;
                outline: none;
            }
        """)
        search_container.addWidget(self.search_input)
        search_layout.addLayout(search_container)
        
        # Add vehicle button
        add_btn = QPushButton("+ Novo Veículo")
        add_btn.setFixedWidth(150)
        add_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        add_btn.clicked.connect(self.add_vehicle)
        search_layout.addWidget(add_btn)
        
        layout.addLayout(search_layout)
        
        # Help text
        help_text = QLabel("💡 Dica: Clique duplo para editar ou botão direito para mais opções")
        help_text.setStyleSheet("color: #6c757d; margin-top: 5px;")
        layout.addWidget(help_text)
        
        # Vehicles table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Placa", "Modelo", "Cor", "Status"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                gridline-color: #dee2e6;
                border: none;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #dee2e6;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #e8f0fe;
                color: black;
            }
        """)
        
        # Enable sorting
        self.table.setSortingEnabled(True)
        
        # Setup context menu
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Setup double-click handling
        self.table.doubleClicked.connect(self.edit_vehicle)
        
        layout.addWidget(self.table)
    
    def load_vehicles(self):
        """Load vehicles into table."""
        try:
            # Get search filter
            search = self.search_input.text().strip()
            
            # Get vehicles from repository
            vehicles = self.vehicle_repo.get_all()
            
            # Filter if search text exists
            if search:
                vehicles = [v for v in vehicles if search.lower() in v['plate'].lower()]
            
            # Update table
            self.table.setRowCount(len(vehicles))
            for row, vehicle in enumerate(vehicles):
                self.table.setItem(row, 0, QTableWidgetItem(vehicle['plate']))
                self.table.setItem(row, 1, QTableWidgetItem(vehicle['model']))
                self.table.setItem(row, 2, QTableWidgetItem(vehicle.get('color', '')))
                self.table.setItem(row, 3, QTableWidgetItem(vehicle['status']))
                
            # Adjust columns
            self.table.resizeColumnsToContents()
            
        except Exception as e:
            QMessageBox.warning(
                self,
                'Erro',
                f'Erro ao carregar veículos: {str(e)}',
                QMessageBox.Ok
            )
            
    def add_vehicle(self):
        """Open dialog to add a new vehicle."""
        try:
            dialog = VehicleFormDialog(parent=self)
            if dialog.exec_():
                self.load_vehicles()
        except Exception as e:
            QMessageBox.critical(
                self,
                'Erro',
                f'Erro ao adicionar veículo: {str(e)}',
                QMessageBox.Ok
            )
            
    def edit_vehicle(self, index=None):
        """Open dialog to edit selected vehicle."""
        try:
            if index is None:
                index = self.table.currentIndex()
                
            if not index.isValid():
                return
                
            plate = self.table.item(index.row(), 0).text()
            vehicle = self.vehicle_repo.get_vehicle_by_plate(plate)
            
            if vehicle:
                dialog = VehicleFormDialog(vehicle, parent=self)
                if dialog.exec_():
                    self.load_vehicles()
        except Exception as e:
            QMessageBox.warning(
                self,
                'Erro',
                f'Erro ao editar veículo: {str(e)}',
                QMessageBox.Ok
            )
                
    def delete_vehicle(self):
        """Delete selected vehicle after confirmation."""
        try:
            index = self.table.currentIndex()
            if not index.isValid():
                return
                
            plate = self.table.item(index.row(), 0).text()
            
            reply = QMessageBox.question(
                self,
                'Confirmar Exclusão',
                f'Tem certeza que deseja excluir o veículo {plate}?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.vehicle_repo.delete(plate)
                self.load_vehicles()
        except Exception as e:
            QMessageBox.warning(
                self,
                'Erro',
                f'Erro ao excluir veículo: {str(e)}',
                QMessageBox.Ok
            )
            
    def export_data(self):
        """Export vehicles data to CSV."""
        try:
            # Get all vehicles
            vehicles = self.vehicle_repo.get_all()
            
            # Let user choose save location
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Exportar Dados",
                "",
                "CSV Files (*.csv)"
            )
            
            if file_path:
                # Ensure .csv extension
                if not file_path.lower().endswith('.csv'):
                    file_path += '.csv'
                
                # Define headers for export
                headers = ['Placa', 'Modelo', 'Cor', 'Status']
                
                # Export data
                self.exporter.export_to_csv(
                    data=vehicles,
                    headers=headers,
                    field_names=['plate', 'model', 'color', 'status'],
                    file_path=file_path
                )
                
                QMessageBox.information(
                    self,
                    'Sucesso',
                    'Dados exportados com sucesso!',
                    QMessageBox.Ok
                )
                
        except Exception as e:
            QMessageBox.warning(
                self,
                'Erro',
                f'Erro ao exportar dados: {str(e)}',
                QMessageBox.Ok
            )
            
    def show_context_menu(self, position):
        """Show context menu for vehicle operations."""
        try:
            index = self.table.indexAt(position)
            if not index.isValid():
                return
                
            menu = QMenu(self)
            
            edit_action = menu.addAction("✏️ Editar")
            delete_action = menu.addAction("🗑️ Excluir")
            
            action = menu.exec_(self.table.viewport().mapToGlobal(position))
            
            if action == edit_action:
                self.edit_vehicle(index)
            elif action == delete_action:
                self.delete_vehicle()
        except Exception as e:
            QMessageBox.warning(
                self,
                'Erro',
                f'Erro ao mostrar menu: {str(e)}',
                QMessageBox.Ok
            )