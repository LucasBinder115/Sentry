"""Placeholder Transportes (Shipments) view implementation.
This view is intentionally minimal and does not introduce shipment-specific logic yet.
"""

from PyQt5.QtWidgets import QVBoxLayout, QLabel, QMessageBox

from .base_section_view import BaseSectionView


class TransportesView(BaseSectionView):
    """Transportes management view (placeholder)."""

    def __init__(self, parent=None):
        super().__init__("Gestão de Transportes", parent)
        self.setup_content()

    def setup_content(self):
        """Setup minimal placeholder content."""
        layout = QVBoxLayout(self.content_area)
        info = QLabel(
            "Esta seção de Transportes é um placeholder.\n"
            "Em breve: listagem, filtros e ações de transporte."
        )
        info.setStyleSheet("color: #6c757d;")
        layout.addWidget(info)

    def refresh(self):
        """Refresh view (no-op for placeholder)."""
        pass

    def export_data(self):
        """Export placeholder (not implemented)."""
        QMessageBox.information(
            self,
            "Exportar",
            "Exportação de Transportes ainda não implementada.",
            QMessageBox.Ok,
        )
