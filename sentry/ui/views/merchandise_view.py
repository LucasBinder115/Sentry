"""Merchandise section view implementation."""

from PyQt5.QtWidgets import (
    QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QLineEdit, QLabel,
    QComboBox, QMenu, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt

from .base_section_view import BaseSectionView
from ..widgets.merchandise_form_dialog import MerchandiseFormDialog
from ...data.database.merchandise_repository import MerchandiseRepository
from ...core.export import DataExporter
from ...config import EXPORTS_DIR


class MerchandiseView(BaseSectionView):
    """Merchandise management view."""

    def __init__(self, parent=None):
        """Initialize merchandise view."""
        super().__init__("Controle de Mercadorias", parent)
        self.merch_repo = MerchandiseRepository()
        self.exporter = DataExporter(EXPORTS_DIR)
        self.setup_content()
        self.load_merchandise()

    def setup_content(self):
        """Setup the merchandise view content."""
        layout = QVBoxLayout(self.content_area)

        # Filters bar
        filters_layout = QHBoxLayout()

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nome ou descrição...")
        self.search_input.textChanged.connect(self.load_merchandise)
        filters_layout.addWidget(self.search_input)

        # Status filter
        self.status_filter = QComboBox()
        self.status_filter.addItems(["Todos", "ATIVO", "INATIVO", "EM FALTA"])
        self.status_filter.currentIndexChanged.connect(self.load_merchandise)
        filters_layout.addWidget(QLabel("Status:"))
        filters_layout.addWidget(self.status_filter)

        # Add merchandise button
        add_btn = QPushButton("+ Nova Mercadoria")
        add_btn.setFixedWidth(160)
        add_btn.clicked.connect(self.add_merchandise)
        filters_layout.addWidget(add_btn)

        layout.addLayout(filters_layout)

        # Help text
        help_text = QLabel("💡 Dica: Clique duplo para editar ou botão direito para mais opções")
        help_text.setStyleSheet("color: #6c757d; margin-top: 5px;")
        layout.addWidget(help_text)

        # Merchandise table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Nome", "Unidade", "Quantidade", "Status", "Atualizado em"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.doubleClicked.connect(self.edit_merchandise)
        layout.addWidget(self.table)

    def load_merchandise(self):
        """Load merchandise from repository into table."""
        try:
            search = self.search_input.text().strip().lower()
            status_filter = self.status_filter.currentText()

            items = self.merch_repo.get_all()

            # Filter by search
            if search:
                items = [m for m in items if
                         search in (m.get('name') or '').lower() or
                         search in (m.get('description') or '').lower()]

            # Filter by status (note: get_all returns only ACTIVE by default in repo)
            if status_filter != "Todos":
                items = [m for m in items if (m.get('status') or '').upper() == status_filter.upper()]

            self.table.setRowCount(len(items))
            for row, m in enumerate(items):
                # Store id in the first cell for operations
                name_item = QTableWidgetItem(m.get('name', ''))
                name_item.setData(Qt.UserRole, m.get('id'))
                self.table.setItem(row, 0, name_item)
                self.table.setItem(row, 1, QTableWidgetItem(m.get('unit', '')))
                self.table.setItem(row, 2, QTableWidgetItem(str(m.get('quantity', 0))))
                self.table.setItem(row, 3, QTableWidgetItem(m.get('status', '')))
                self.table.setItem(row, 4, QTableWidgetItem(str(m.get('updated_at', ''))))

            self.table.resizeColumnsToContents()
        except Exception as e:
            QMessageBox.warning(
                self,
                'Erro',
                f'Erro ao carregar mercadorias: {str(e)}',
                QMessageBox.Ok
            )

    def add_merchandise(self):
        """Open dialog to add a new merchandise item."""
        try:
            dialog = MerchandiseFormDialog(parent=self)
            if dialog.exec_():
                self.load_merchandise()
        except Exception as e:
            QMessageBox.critical(
                self,
                'Erro',
                f'Erro ao adicionar mercadoria: {str(e)}',
                QMessageBox.Ok
            )

    def edit_merchandise(self, index=None):
        """Open dialog to edit selected merchandise item."""
        try:
            if index is None:
                index = self.table.currentIndex()
            if not index.isValid():
                return

            # Retrieve id stored in first column
            id_item = self.table.item(index.row(), 0)
            merch_id = id_item.data(Qt.UserRole)
            if merch_id is None:
                return

            # Load full record by id
            item = self.merch_repo.get_by_id(merch_id)
            item = dict(item) if item else None
            if item:
                dialog = MerchandiseFormDialog(item, parent=self)
                if dialog.exec_():
                    self.load_merchandise()
        except Exception as e:
            QMessageBox.warning(
                self,
                'Erro',
                f'Erro ao editar mercadoria: {str(e)}',
                QMessageBox.Ok
            )

    def delete_merchandise(self):
        """Delete selected merchandise after confirmation (soft delete)."""
        try:
            index = self.table.currentIndex()
            if not index.isValid():
                return

            id_item = self.table.item(index.row(), 0)
            merch_id = id_item.data(Qt.UserRole)
            name = id_item.text()

            reply = QMessageBox.question(
                self,
                'Confirmar Exclusão',
                f'Tem certeza que deseja excluir a mercadoria "{name}"?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes and merch_id is not None:
                self.merch_repo.delete(int(merch_id))
                self.load_merchandise()
        except Exception as e:
            QMessageBox.warning(
                self,
                'Erro',
                f'Erro ao excluir mercadoria: {str(e)}',
                QMessageBox.Ok
            )

    def export_data(self):
        """Export merchandise data to CSV (saved in exports directory)."""
        try:
            items = self.merch_repo.get_all()

            # Map data keys to CSV headers
            headers_map = {
                'name': 'Nome',
                'unit': 'Unidade',
                'quantity': 'Quantidade',
                'status': 'Status',
                'updated_at': 'Atualizado em'
            }

            saved_path = self.exporter.export_to_csv(
                data=items,
                filename='mercadorias',
                headers=headers_map
            )

            QMessageBox.information(
                self,
                'Sucesso',
                f'Dados exportados com sucesso em:\n{saved_path}',
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
        """Show context menu for merchandise operations."""
        try:
            index = self.table.indexAt(position)
            if not index.isValid():
                return

            menu = QMenu(self)
            edit_action = menu.addAction("✏️ Editar")
            delete_action = menu.addAction("🗑️ Excluir")

            action = menu.exec_(self.table.viewport().mapToGlobal(position))
            if action == edit_action:
                self.edit_merchandise(index)
            elif action == delete_action:
                self.delete_merchandise()
        except Exception as e:
            QMessageBox.warning(
                self,
                'Erro',
                f'Erro ao mostrar menu: {str(e)}',
                QMessageBox.Ok
            )

    def refresh(self):
        """Refresh current data."""
        self.load_merchandise()