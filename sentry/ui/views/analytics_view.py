"""Analytics view with date filters, charts, and exports."""

from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QDateEdit, QMessageBox, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QDate

try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    _HAS_MPL = True
except Exception:
    FigureCanvas = None
    Figure = None
    _HAS_MPL = False

from ...data.database.access_log_repository import AccessLogRepository
from ...data.database.vehicle_repository import VehicleRepository
from ...data.database.merchandise_repository import MerchandiseRepository
from ...data.database.carrier_repository import CarrierRepository
from ...core.export import DataExporter
from ...config import EXPORTS_DIR
from ...core.event_bus import get_event_bus

import os
from pathlib import Path
import csv
import zipfile


class AnalyticsView(QWidget):
    """Analytics and reports UI."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.access_repo = AccessLogRepository()
        self.vehicle_repo = VehicleRepository()
        self.merch_repo = MerchandiseRepository()
        self.carrier_repo = CarrierRepository()
        self.exporter = DataExporter(EXPORTS_DIR)
        self._setup_ui()
        self._load_analytics()
        # Subscribe to OCR events for live updates
        try:
            get_event_bus().subscribe('ocr.scan_completed', self._on_scan_completed)
        except Exception:
            pass

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        title = QLabel("📈 Analytics")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # Date range
        range_row = QHBoxLayout()
        range_row.addWidget(QLabel("Início:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-6))
        range_row.addWidget(self.start_date)
        range_row.addWidget(QLabel("Fim:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        range_row.addWidget(self.end_date)
        apply_btn = QPushButton("Aplicar")
        apply_btn.clicked.connect(self._load_analytics)
        range_row.addWidget(apply_btn)
        range_row.addStretch()
        layout.addLayout(range_row)

        # Charts container
        charts_row = QHBoxLayout()

        # Daily scans chart
        self.daily_frame = QFrame()
        self.daily_layout = QVBoxLayout(self.daily_frame)
        self.daily_layout.addWidget(QLabel("Scans por Dia"))
        if _HAS_MPL:
            self.daily_fig = Figure(figsize=(4, 3))
            self.daily_canvas = FigureCanvas(self.daily_fig)
            self.daily_layout.addWidget(self.daily_canvas)
        else:
            self.daily_layout.addWidget(QLabel("matplotlib não instalado"))
        charts_row.addWidget(self.daily_frame)

        # Accuracy chart (simple text KPI + bar when mpl available)
        self.accuracy_frame = QFrame()
        self.accuracy_layout = QVBoxLayout(self.accuracy_frame)
        self.accuracy_layout.addWidget(QLabel("Acurácia do OCR"))
        if _HAS_MPL:
            self.acc_fig = Figure(figsize=(4, 3))
            self.acc_canvas = FigureCanvas(self.acc_fig)
            self.accuracy_layout.addWidget(self.acc_canvas)
        else:
            self.accuracy_layout.addWidget(QLabel("matplotlib não instalado"))
        charts_row.addWidget(self.accuracy_frame)

        layout.addLayout(charts_row)

        # Second row of charts: Carrier performance and Cargo distribution
        charts_row2 = QHBoxLayout()

        # Carrier performance
        self.carrier_frame = QFrame()
        self.carrier_layout = QVBoxLayout(self.carrier_frame)
        self.carrier_layout.addWidget(QLabel("Performance por Transportadora"))
        if _HAS_MPL:
            self.carrier_fig = Figure(figsize=(4, 3))
            self.carrier_canvas = FigureCanvas(self.carrier_fig)
            self.carrier_layout.addWidget(self.carrier_canvas)
        else:
            self.carrier_layout.addWidget(QLabel("matplotlib não instalado"))
        charts_row2.addWidget(self.carrier_frame)

        # Cargo distribution
        self.cargo_frame = QFrame()
        self.cargo_layout = QVBoxLayout(self.cargo_frame)
        self.cargo_layout.addWidget(QLabel("Distribuição de Carga (Categoria)"))
        if _HAS_MPL:
            self.cargo_fig = Figure(figsize=(4, 3))
            self.cargo_canvas = FigureCanvas(self.cargo_fig)
            self.cargo_layout.addWidget(self.cargo_canvas)
        else:
            self.cargo_layout.addWidget(QLabel("matplotlib não instalado"))
        charts_row2.addWidget(self.cargo_frame)

        layout.addLayout(charts_row2)

        # Top vehicles list
        top_row = QHBoxLayout()
        self.top_list = QListWidget()
        top_container = QVBoxLayout()
        top_container.addWidget(QLabel("Veículos Mais Frequentes"))
        top_container.addWidget(self.top_list)
        top_frame = QFrame()
        top_frame.setLayout(top_container)
        top_row.addWidget(top_frame)
        layout.addLayout(top_row)

        # Export buttons
        export_row = QHBoxLayout()
        pdf_btn = QPushButton("📄 Exportar Relatório (PDF)")
        pdf_btn.clicked.connect(self._export_pdf)
        export_row.addWidget(pdf_btn)
        zip_btn = QPushButton("🗂️ Exportar Todos (ZIP)")
        zip_btn.clicked.connect(self._export_all_zip)
        export_row.addWidget(zip_btn)
        export_row.addStretch()
        layout.addLayout(export_row)

    def _get_range_iso(self):
        sd = self.start_date.date().toPyDate()
        ed = self.end_date.date().toPyDate()
        start_iso = datetime.combine(sd, datetime.min.time()).isoformat()
        end_iso = datetime.combine(ed, datetime.max.time()).isoformat()
        return start_iso, end_iso

    def _load_analytics(self):
        try:
            start_iso, end_iso = self._get_range_iso()
            # Daily counts
            by_day = self.access_repo.get_counts_by_day(start_iso, end_iso)
            # Accuracy
            acc = self.access_repo.get_accuracy_stats(start_iso, end_iso)
            # Top vehicles
            topv = self.access_repo.get_top_vehicles(start_iso, end_iso, limit=10)
            # Top carriers
            try:
                topc = self.access_repo.get_top_carriers(start_iso, end_iso, limit=10)
            except Exception:
                topc = []
            # Cargo distribution
            try:
                catdist = self.merch_repo.get_category_distribution()
            except Exception:
                catdist = []

            if _HAS_MPL:
                # Render daily chart
                self.daily_fig.clear()
                ax = self.daily_fig.add_subplot(111)
                days = [row['day'] for row in by_day]
                vals = [row['total'] for row in by_day]
                ax.bar(days, vals, color="#3498db", alpha=0.7, label='Diário')
                # Moving average (3-day)
                if len(vals) >= 2:
                    import numpy as _np
                    window = 3
                    if len(vals) >= window:
                        kernel = _np.ones(window) / window
                        ma = _np.convolve(vals, kernel, mode='valid')
                        # align x for MA
                        ma_x = days[window-1:]
                        ax.plot(ma_x, ma, color="#2ecc71", marker='o', linewidth=2, label=f"Média {window}d")
                ax.tick_params(axis='x', rotation=45)
                ax.set_ylabel("Scans")
                ax.grid(axis='y', linestyle='--', alpha=0.3)
                ax.legend(loc='upper left')
                self.daily_canvas.draw()

                # Render accuracy chart
                self.acc_fig.clear()
                ax2 = self.acc_fig.add_subplot(111)
                labels = ["Autorizado", "Não Autorizado"]
                values = [acc.get('authorized',0), acc.get('unauthorized',0)]
                colors = ["#2ecc71", "#e74c3c"]
                if sum(values) > 0:
                    wedges, texts, autotexts = ax2.pie(values, labels=labels, autopct='%1.0f%%', startangle=140, colors=colors)
                    ax2.axis('equal')
                else:
                    ax2.bar(labels, values, color=colors)
                    ax2.set_ylabel("Total")
                self.acc_canvas.draw()

                # Render carrier performance chart
                self.carrier_fig.clear()
                ax3 = self.carrier_fig.add_subplot(111)
                if topc:
                    names = [row['carrier'] for row in topc]
                    counts = [row['cnt'] for row in topc]
                    ax3.barh(names, counts, color="#8e44ad")
                    ax3.set_xlabel("Viagens")
                else:
                    ax3.text(0.5, 0.5, "Sem dados de transportadoras\nou vínculo ausente", ha='center', va='center')
                    ax3.set_axis_off()
                self.carrier_canvas.draw()

                # Render cargo distribution chart
                self.cargo_fig.clear()
                ax4 = self.cargo_fig.add_subplot(111)
                if catdist and sum((row.get('total_quantity') or 0) for row in catdist) > 0:
                    labels = [row['category'] for row in catdist]
                    values = [row['total_quantity'] for row in catdist]
                    ax4.pie(values, labels=labels, autopct='%1.0f%%', startangle=140)
                    ax4.axis('equal')
                elif catdist:
                    labels = [row['category'] for row in catdist]
                    values = [row['items'] for row in catdist]
                    ax4.bar(labels, values, color="#16a085")
                    ax4.tick_params(axis='x', rotation=45)
                    ax4.set_ylabel("Itens")
                else:
                    ax4.text(0.5, 0.5, "Sem dados de categorias", ha='center', va='center')
                    ax4.set_axis_off()
                self.cargo_canvas.draw()

            # Populate top vehicles
            self.top_list.clear()
            for row in topv:
                item = QListWidgetItem(f"{row['plate']}: {row['cnt']}")
                self.top_list.addItem(item)
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Falha ao carregar analytics: {e}")

    def refresh(self):
        """Refresh hook used by dashboard on tab switch."""
        self._load_analytics()

    def _on_scan_completed(self, payload: dict):
        """Live-update analytics when a scan completes within the selected range."""
        try:
            # Only refresh if end_date includes today (common case)
            if self.end_date.date() >= QDate.currentDate():
                self._load_analytics()
        except Exception:
            pass

    def _export_all_zip(self):
        try:
            # Prepare CSVs using DataExporter
            vehicles = self.vehicle_repo.get_all()
            merch = self.merch_repo.get_all()
            carriers = self.carrier_repo.get_all()
            logs = self.access_repo.get_recent_with_vehicle(1000)

            v_path = self.exporter.export_to_csv(vehicles, 'veiculos', {'plate':'Placa','model':'Modelo','color':'Cor','status':'Status'})
            m_path = self.exporter.export_to_csv(merch, 'mercadorias', {'name':'Nome','unit':'Unidade','quantity':'Quantidade','status':'Status'})
            c_path = self.exporter.export_to_csv(carriers, 'transportadoras', {'name':'Nome','cnpj':'CNPJ','contact_phone':'Telefone','status':'Status'})
            l_path = self.exporter.export_to_csv(logs, 'acessos', {'id':'ID','plate':'Placa','model':'Modelo','status':'Status','created_at':'Data'})

            stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            zip_path = EXPORTS_DIR / f"export_all_{stamp}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for p in [v_path, m_path, c_path, l_path]:
                    zf.write(p, arcname=Path(p).name)

            QMessageBox.information(self, 'Exportar', f'Exportação concluída:\n{zip_path}')
        except Exception as e:
            QMessageBox.warning(self, 'Erro', f'Erro ao exportar: {e}')

    def _export_pdf(self):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import cm
        except Exception:
            QMessageBox.warning(self, 'PDF', 'reportlab não instalado. Adicione ao requirements.txt')
            return

        try:
            start_iso, end_iso = self._get_range_iso()
            by_day = self.access_repo.get_counts_by_day(start_iso, end_iso)
            acc = self.access_repo.get_accuracy_stats(start_iso, end_iso)
            topv = self.access_repo.get_top_vehicles(start_iso, end_iso, limit=10)

            stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pdf_path = EXPORTS_DIR / f"relatorio_{stamp}.pdf"
            c = canvas.Canvas(str(pdf_path), pagesize=A4)
            width, height = A4

            c.setFont("Helvetica-Bold", 16)
            c.drawString(2*cm, height-2*cm, "Relatório de Analytics")
            c.setFont("Helvetica", 10)
            c.drawString(2*cm, height-2.7*cm, f"Período: {start_iso} a {end_iso}")

            # Accuracy
            c.setFont("Helvetica-Bold", 12)
            c.drawString(2*cm, height-4*cm, "Acurácia do OCR")
            c.setFont("Helvetica", 10)
            c.drawString(2*cm, height-4.6*cm, f"Authorized: {acc.get('authorized',0)}")
            c.drawString(2*cm, height-5.1*cm, f"Unauthorized: {acc.get('unauthorized',0)}")
            c.drawString(2*cm, height-5.6*cm, f"Accuracy: {acc.get('accuracy_pct',0)}%")

            # Daily table (first 10 rows)
            c.setFont("Helvetica-Bold", 12)
            c.drawString(2*cm, height-7*cm, "Scans por Dia")
            c.setFont("Helvetica", 10)
            y = height-7.6*cm
            for row in by_day[:10]:
                c.drawString(2*cm, y, f"{row['day']}: {row['total']}")
                y -= 0.5*cm

            # Top vehicles
            c.setFont("Helvetica-Bold", 12)
            c.drawString(12*cm, height-7*cm, "Top Veículos")
            c.setFont("Helvetica", 10)
            y2 = height-7.6*cm
            for row in topv[:10]:
                c.drawString(12*cm, y2, f"{row['plate']}: {row['cnt']}")
                y2 -= 0.5*cm

            c.showPage()
            c.save()
            QMessageBox.information(self, 'PDF', f'Relatório salvo em:\n{pdf_path}')
        except Exception as e:
            QMessageBox.warning(self, 'Erro', f'Erro ao gerar PDF: {e}')
