# sentry/infra/services/pdf_generator.py

import os
import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

from reportlab.lib.pagesizes import letter, A4, A3, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, 
    Spacer, Image, PageBreak, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.legends import Legend

# Configuração de logging
logger = logging.getLogger(__name__)


# Exceções customizadas
class PdfGenerationError(Exception):
    """Exceção base para erros de geração de PDF."""
    pass


class InvalidDataError(PdfGenerationError):
    """Exceção para dados inválidos para geração de PDF."""
    pass


class FileSystemError(PdfGenerationError):
    """Exceção para erros de sistema de arquivos."""
    pass


class ReportType(Enum):
    """Tipos de relatórios disponíveis."""
    ACCESS_REPORT = "access_report"
    CARRIER_REPORT = "carrier_report"
    VEHICLE_REPORT = "vehicle_report"
    MERCHANDISE_REPORT = "merchandise_report"
    SECURITY_REPORT = "security_report"
    CUSTOM_REPORT = "custom_report"


@dataclass
class PdfConfig:
    """Configuração para geração de PDF."""
    page_size: tuple = A4
    orientation: str = "portrait"  # "portrait" ou "landscape"
    title: str = "Relatório Sentry Logística"
    author: str = "Sentry Logística"
    include_logo: bool = True
    logo_path: Optional[Path] = None
    include_timestamp: bool = True
    include_page_numbers: bool = True
    compression: bool = True
    margin_left: float = 1.5 * cm
    margin_right: float = 1.5 * cm
    margin_top: float = 2 * cm
    margin_bottom: float = 2 * cm


@dataclass
class PdfGenerationResult:
    """Resultado da geração de PDF."""
    file_path: Path
    page_count: int
    file_size: int
    generation_time: float
    report_type: ReportType
    metadata: Dict[str, Any]


class PdfStyleManager:
    """Gerenciador de estilos para PDF."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._register_custom_styles()
        self._register_fonts()
    
    def _register_fonts(self):
        """Registra fontes customizadas (se disponíveis)."""
        try:
            # Tenta registrar fontes comuns - em produção, usar fontes específicas
            pdfmetrics.registerFont(TTFont('Helvetica-Bold', 'Helvetica-Bold'))
        except:
            logger.warning("Fontes customizadas não disponíveis, usando padrão")
    
    def _register_custom_styles(self):
        """Registra estilos customizados."""
        # Estilo para título principal
        self.styles.add(ParagraphStyle(
            name='MainTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1,  # Centro
            textColor=colors.HexColor('#2C3E50')
        ))
        
        # Estilo para subtítulo
        self.styles.add(ParagraphStyle(
            name='SubTitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=20,
            textColor=colors.HexColor('#34495E')
        ))
        
        # Estilo para cabeçalho de seção
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading3'],
            fontSize=12,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.HexColor('#16A085')
        ))
        
        # Estilo para dados destacados
        self.styles.add(ParagraphStyle(
            name='Highlight',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#E74C3C'),
            backColor=colors.HexColor('#FDEDEC')
        ))
        
        # Estilo para rodapé
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.grey
        ))
    
    def get_table_style(self, style_type: str = "default") -> TableStyle:
        """Retorna estilo de tabela baseado no tipo."""
        if style_type == "header":
            return TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ])
        elif style_type == "zebra":
            return TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9F9')]),
            ])
        else:  # default
            return TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ])


class PdfContentBuilder:
    """Construtor de conteúdo para PDF."""
    
    def __init__(self, style_manager: PdfStyleManager):
        self.style_manager = style_manager
        self.elements = []
    
    def add_title(self, title: str, subtitle: Optional[str] = None):
        """Adiciona título e subtítulo."""
        self.elements.append(Paragraph(title, self.style_manager.styles['MainTitle']))
        if subtitle:
            self.elements.append(Paragraph(subtitle, self.style_manager.styles['SubTitle']))
        self.elements.append(Spacer(1, 0.3 * inch))
    
    def add_section_header(self, header: str):
        """Adiciona cabeçalho de seção."""
        self.elements.append(Paragraph(header, self.style_manager.styles['SectionHeader']))
    
    def add_paragraph(self, text: str, style: str = 'Normal'):
        """Adiciona parágrafo de texto."""
        self.elements.append(Paragraph(text, self.style_manager.styles[style]))
        self.elements.append(Spacer(1, 0.1 * inch))
    
    def add_table(self, data: List[List[Any]], style: str = "default", col_widths: Optional[List[float]] = None):
        """Adiciona tabela."""
        if not data:
            self.add_paragraph("Nenhum dado disponível para exibição.")
            return
        
        table = Table(data, colWidths=col_widths)
        table_style = self.style_manager.get_table_style(style)
        table.setStyle(table_style)
        self.elements.append(Spacer(1, 0.2 * inch))
        self.elements.append(table)
        self.elements.append(Spacer(1, 0.3 * inch))
    
    def add_key_value_section(self, data: Dict[str, Any], title: Optional[str] = None):
        """Adiciona seção de chave-valor."""
        if title:
            self.add_section_header(title)
        
        table_data = []
        for key, value in data.items():
            table_data.append([f"<b>{key}:</b>", str(value)])
        
        self.add_table(table_data, style="zebra", col_widths=[2.5 * inch, 4 * inch])
    
    def add_statistics(self, stats: Dict[str, Any]):
        """Adiciona seção de estatísticas."""
        self.add_section_header("Estatísticas")
        
        table_data = [["Métrica", "Valor"]]
        for key, value in stats.items():
            table_data.append([key, str(value)])
        
        self.add_table(table_data, style="zebra")
    
    def add_page_break(self):
        """Adiciona quebra de página."""
        self.elements.append(PageBreak())
    
    def add_spacer(self, height: float = 0.2 * inch):
        """Adiciona espaçamento."""
        self.elements.append(Spacer(1, height))
    
    def get_elements(self) -> List[Any]:
        """Retorna todos os elementos construídos."""
        return self.elements


class PdfGenerator:
    """
    Serviço robusto para geração de relatórios PDF.
    
    Suporta múltiplos tipos de relatórios com layouts otimizados
    para diferentes tipos de dados do sistema Sentry.
    """
    
    def __init__(self, config: Optional[PdfConfig] = None):
        self.config = config or PdfConfig()
        self.style_manager = PdfStyleManager()
        logger.info("PDF Generator inicializado")
    
    def generate_access_report(
        self, 
        access_data: List[Dict[str, Any]], 
        file_path: Union[str, Path],
        title: str = "Relatório de Acessos",
        period: Optional[str] = None
    ) -> PdfGenerationResult:
        """
        Gera relatório de acessos de veículos.
        
        Args:
            access_data: Dados de acesso
            file_path: Caminho do arquivo de saída
            title: Título do relatório
            period: Período do relatório
            
        Returns:
            PdfGenerationResult: Resultado da geração
        """
        start_time = datetime.now()
        file_path = Path(file_path)
        
        logger.info("Gerando relatório de acessos: %s", file_path)
        
        try:
            self._ensure_output_directory(file_path)
            
            # Prepara documento
            doc = self._create_document(file_path, title)
            builder = PdfContentBuilder(self.style_manager)
            
            # Cabeçalho
            subtitle = f"Período: {period}" if period else f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            builder.add_title(title, subtitle)
            
            # Estatísticas resumidas
            stats = self._calculate_access_stats(access_data)
            builder.add_statistics(stats)
            
            # Tabela detalhada de acessos
            builder.add_section_header("Detalhamento de Acessos")
            table_data = self._prepare_access_table_data(access_data)
            builder.add_table(table_data, style="zebra")
            
            # Gráficos (se houver dados suficientes)
            if len(access_data) > 5:
                builder.add_page_break()
                builder.add_section_header("Análise Gráfica")
                # Aqui poderia adicionar gráficos usando reportlab.graphics
            
            # Gera PDF
            page_count = self._build_pdf(doc, builder.get_elements())
            
            return self._create_result(
                file_path, page_count, start_time, 
                ReportType.ACCESS_REPORT, len(access_data)
            )
            
        except Exception as e:
            logger.error("Erro na geração do relatório de acessos: %s", e)
            raise PdfGenerationError(f"Erro no relatório de acessos: {str(e)}") from e
    
    def generate_carrier_report(
        self,
        carrier_data: Dict[str, Any],
        vehicles_data: List[Dict[str, Any]],
        file_path: Union[str, Path],
        title: str = "Relatório da Transportadora"
    ) -> PdfGenerationResult:
        """
        Gera relatório completo de transportadora.
        
        Args:
            carrier_data: Dados da transportadora
            vehicles_data: Dados dos veículos
            file_path: Caminho do arquivo de saída
            title: Título do relatório
            
        Returns:
            PdfGenerationResult: Resultado da geração
        """
        start_time = datetime.now()
        file_path = Path(file_path)
        
        logger.info("Gerando relatório da transportadora: %s", file_path)
        
        try:
            self._ensure_output_directory(file_path)
            doc = self._create_document(file_path, title)
            builder = PdfContentBuilder(self.style_manager)
            
            # Cabeçalho
            carrier_name = carrier_data.get('name', 'N/A')
            builder.add_title(title, f"Transportadora: {carrier_name}")
            
            # Informações da transportadora
            builder.add_section_header("Informações Cadastrais")
            carrier_info = {
                'Nome': carrier_data.get('name'),
                'CNPJ': carrier_data.get('cnpj'),
                'Responsável': carrier_data.get('responsible_name'),
                'Telefone': carrier_data.get('contact_phone'),
                'Email': carrier_data.get('email'),
                'Status': carrier_data.get('status', 'Ativa')
            }
            builder.add_key_value_section(carrier_info)
            
            # Endereço
            address = carrier_data.get('address', {})
            if address:
                builder.add_section_header("Endereço")
                address_info = {
                    'Logradouro': address.get('street'),
                    'Número': address.get('number'),
                    'Complemento': address.get('complement'),
                    'Bairro': address.get('neighborhood'),
                    'Cidade': address.get('city'),
                    'Estado': address.get('state'),
                    'CEP': address.get('zip_code')
                }
                builder.add_key_value_section(address_info)
            
            # Frota de veículos
            builder.add_page_break()
            builder.add_section_header("Frota de Veículos")
            
            if vehicles_data:
                table_data = self._prepare_vehicles_table_data(vehicles_data)
                builder.add_table(table_data, style="zebra")
                
                # Estatísticas da frota
                fleet_stats = self._calculate_fleet_stats(vehicles_data)
                builder.add_statistics(fleet_stats)
            else:
                builder.add_paragraph("Nenhum veículo cadastrado para esta transportadora.")
            
            page_count = self._build_pdf(doc, builder.get_elements())
            
            return self._create_result(
                file_path, page_count, start_time,
                ReportType.CARRIER_REPORT, len(vehicles_data)
            )
            
        except Exception as e:
            logger.error("Erro na geração do relatório da transportadora: %s", e)
            raise PdfGenerationError(f"Erro no relatório da transportadora: {str(e)}") from e
    
    def generate_vehicle_report(
        self,
        vehicle_data: Dict[str, Any],
        access_history: List[Dict[str, Any]],
        maintenance_history: List[Dict[str, Any]],
        file_path: Union[str, Path]
    ) -> PdfGenerationResult:
        """
        Gera relatório completo de veículo.
        
        Args:
            vehicle_data: Dados do veículo
            access_history: Histórico de acessos
            maintenance_history: Histórico de manutenção
            file_path: Caminho do arquivo de saída
            
        Returns:
            PdfGenerationResult: Resultado da geração
        """
        start_time = datetime.now()
        file_path = Path(file_path)
        
        logger.info("Gerando relatório do veículo: %s", file_path)
        
        try:
            self._ensure_output_directory(file_path)
            doc = self._create_document(file_path, "Relatório do Veículo")
            builder = PdfContentBuilder(self.style_manager)
            
            # Cabeçalho
            plate = vehicle_data.get('plate', 'N/A')
            model = vehicle_data.get('model', 'N/A')
            builder.add_title("Relatório do Veículo", f"Placa: {plate} - Modelo: {model}")
            
            # Informações do veículo
            builder.add_section_header("Informações do Veículo")
            vehicle_info = {
                'Placa': vehicle_data.get('plate'),
                'Modelo': vehicle_data.get('model'),
                'Cor': vehicle_data.get('color'),
                'Tipo': vehicle_data.get('type'),
                'Ano': vehicle_data.get('year'),
                'Chassi': vehicle_data.get('chassis_number'),
                'Combustível': vehicle_data.get('fuel_type'),
                'Capacidade (kg)': vehicle_data.get('capacity_kg'),
                'Capacidade (m³)': vehicle_data.get('capacity_m3'),
                'Status': vehicle_data.get('status')
            }
            builder.add_key_value_section(vehicle_info)
            
            # Transportadora
            carrier_info = {
                'CNPJ': vehicle_data.get('carrier_cnpj'),
                'Nome': vehicle_data.get('carrier_name')
            }
            builder.add_key_value_section(carrier_info, "Transportadora")
            
            # Histórico de acessos
            builder.add_page_break()
            builder.add_section_header("Histórico de Acessos (Últimos 30)")
            
            if access_history:
                table_data = self._prepare_access_history_table_data(access_history[:30])  # Limita a 30 registros
                builder.add_table(table_data, style="zebra")
            else:
                builder.add_paragraph("Nenhum registro de acesso encontrado.")
            
            # Histórico de manutenção
            if maintenance_history:
                builder.add_page_break()
                builder.add_section_header("Histórico de Manutenção")
                table_data = self._prepare_maintenance_table_data(maintenance_history)
                builder.add_table(table_data, style="zebra")
            
            page_count = self._build_pdf(doc, builder.get_elements())
            
            return self._create_result(
                file_path, page_count, start_time,
                ReportType.VEHICLE_REPORT, len(access_history)
            )
            
        except Exception as e:
            logger.error("Erro na geração do relatório do veículo: %s", e)
            raise PdfGenerationError(f"Erro no relatório do veículo: {str(e)}") from e
    
    def generate_custom_report(
        self,
        data: Dict[str, Any],
        file_path: Union[str, Path],
        template: str = "default"
    ) -> PdfGenerationResult:
        """
        Gera relatório customizado baseado em template.
        
        Args:
            data: Dados para o relatório
            file_path: Caminho do arquivo de saída
            template: Template a ser usado
            
        Returns:
            PdfGenerationResult: Resultado da geração
        """
        # Implementação para relatórios customizados
        # Pode ser extendido para diferentes templates
        pass
    
    def _create_document(self, file_path: Path, title: str) -> SimpleDocTemplate:
        """Cria documento PDF com configurações."""
        if self.config.orientation == "landscape":
            page_size = landscape(self.config.page_size)
        else:
            page_size = self.config.page_size
        
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=page_size,
            rightMargin=self.config.margin_right,
            leftMargin=self.config.margin_left,
            topMargin=self.config.margin_top,
            bottomMargin=self.config.margin_bottom,
            title=title,
            author=self.config.author,
            compress=self.config.compression
        )
        
        return doc
    
    def _build_pdf(self, doc: SimpleDocTemplate, elements: List[Any]) -> int:
        """Constrói o PDF e retorna número de páginas."""
        try:
            doc.build(elements)
            
            # Conta páginas (aproximado - em produção, usar método mais preciso)
            # Esta é uma estimativa simples baseada no conteúdo
            estimated_pages = max(1, len(elements) // 20)
            return estimated_pages
            
        except Exception as e:
            raise PdfGenerationError(f"Erro na construção do PDF: {str(e)}") from e
    
    def _ensure_output_directory(self, file_path: Path):
        """Garante que o diretório de saída existe."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise FileSystemError(f"Erro ao criar diretório {file_path.parent}: {str(e)}") from e
    
    def _create_result(
        self, 
        file_path: Path, 
        page_count: int, 
        start_time: datetime,
        report_type: ReportType,
        data_count: int
    ) -> PdfGenerationResult:
        """Cria resultado da geração de PDF."""
        generation_time = (datetime.now() - start_time).total_seconds()
        file_size = file_path.stat().st_size if file_path.exists() else 0
        
        return PdfGenerationResult(
            file_path=file_path,
            page_count=page_count,
            file_size=file_size,
            generation_time=generation_time,
            report_type=report_type,
            metadata={
                'data_records': data_count,
                'generation_timestamp': datetime.now().isoformat()
            }
        )
    
    # Métodos auxiliares para preparação de dados
    def _prepare_access_table_data(self, access_data: List[Dict[str, Any]]) -> List[List[Any]]:
        """Prepara dados para tabela de acessos."""
        headers = ["Placa", "Data/Hora", "Direção", "Portão", "Motorista", "Transportadora"]
        table_data = [headers]
        
        for access in access_data:
            row = [
                access.get('vehicle_plate', 'N/A'),
                access.get('timestamp', 'N/A'),
                access.get('access_type', 'N/A'),
                access.get('gate_number', 'N/A'),
                access.get('driver_name', 'N/A'),
                access.get('carrier_name', 'N/A')
            ]
            table_data.append(row)
        
        return table_data
    
    def _prepare_vehicles_table_data(self, vehicles_data: List[Dict[str, Any]]) -> List[List[Any]]:
        """Prepara dados para tabela de veículos."""
        headers = ["Placa", "Modelo", "Cor", "Tipo", "Ano", "Status"]
        table_data = [headers]
        
        for vehicle in vehicles_data:
            row = [
                vehicle.get('plate', 'N/A'),
                vehicle.get('model', 'N/A'),
                vehicle.get('color', 'N/A'),
                vehicle.get('type', 'N/A'),
                vehicle.get('year', 'N/A'),
                vehicle.get('status', 'N/A')
            ]
            table_data.append(row)
        
        return table_data
    
    def _prepare_access_history_table_data(self, access_history: List[Dict[str, Any]]) -> List[List[Any]]:
        """Prepara dados para tabela de histórico de acessos."""
        headers = ["Data/Hora", "Direção", "Portão", "Motorista", "Alertas"]
        table_data = [headers]
        
        for access in access_history:
            alert_indicator = "⚠️" if access.get('security_alert') else ""
            row = [
                access.get('timestamp', 'N/A'),
                access.get('access_type', 'N/A'),
                access.get('gate_number', 'N/A'),
                access.get('driver_name', 'N/A'),
                alert_indicator
            ]
            table_data.append(row)
        
        return table_data
    
    def _prepare_maintenance_table_data(self, maintenance_data: List[Dict[str, Any]]) -> List[List[Any]]:
        """Prepara dados para tabela de manutenção."""
        headers = ["Data", "Tipo", "Descrição", "Custo (R$)", "Próxima Manutenção"]
        table_data = [headers]
        
        for maintenance in maintenance_data:
            row = [
                maintenance.get('maintenance_date', 'N/A'),
                maintenance.get('maintenance_type', 'N/A'),
                maintenance.get('description', 'N/A')[:50] + "..." if len(maintenance.get('description', '')) > 50 else maintenance.get('description', 'N/A'),
                f"R$ {maintenance.get('cost', 0):.2f}" if maintenance.get('cost') else "N/A",
                maintenance.get('next_maintenance_date', 'N/A')
            ]
            table_data.append(row)
        
        return table_data
    
    def _calculate_access_stats(self, access_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcula estatísticas de acessos."""
        total = len(access_data)
        entries = len([a for a in access_data if a.get('access_type') == 'entry'])
        exits = len([a for a in access_data if a.get('access_type') == 'exit'])
        alerts = len([a for a in access_data if a.get('security_alert')])
        
        return {
            "Total de Acessos": total,
            "Entradas": entries,
            "Saídas": exits,
            "Alertas de Segurança": alerts,
            "Veículos Únicos": len(set(a.get('vehicle_plate') for a in access_data))
        }
    
    def _calculate_fleet_stats(self, vehicles_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcula estatísticas da frota."""
        total = len(vehicles_data)
        active = len([v for v in vehicles_data if v.get('status') == 'active'])
        in_maintenance = len([v for v in vehicles_data if v.get('status') == 'maintenance'])
        
        # Agrupa por tipo
        type_count = {}
        for vehicle in vehicles_data:
            vehicle_type = vehicle.get('type', 'outro')
            type_count[vehicle_type] = type_count.get(vehicle_type, 0) + 1
        
        stats = {
            "Total de Veículos": total,
            "Veículos Ativos": active,
            "Em Manutenção": in_maintenance
        }
        
        # Adiciona contagem por tipo
        for vehicle_type, count in type_count.items():
            stats[f"Tipo {vehicle_type.title()}"] = count
        
        return stats


# Fábrica para criação de geradores de PDF
class PdfGeneratorFactory:
    """Fábrica para criar instâncias de PdfGenerator com configurações comuns."""
    
    @staticmethod
    def create_default_generator() -> PdfGenerator:
        """Cria gerador com configurações padrão."""
        return PdfGenerator()
    
    @staticmethod
    def create_landscape_generator() -> PdfGenerator:
        """Cria gerador otimizado para modo paisagem."""
        config = PdfConfig(orientation="landscape", page_size=A4)
        return PdfGenerator(config)
    
    @staticmethod
    def create_a3_generator() -> PdfGenerator:
        """Cria gerador otimizado para formato A3."""
        config = PdfConfig(page_size=A3, orientation="landscape")
        return PdfGenerator(config)


# Exemplo de uso
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Cria gerador de PDF
        pdf_generator = PdfGeneratorFactory.create_default_generator()
        
        # Dados de exemplo para relatório de acessos
        sample_access_data = [
            {
                'vehicle_plate': 'ABC1D23',
                'timestamp': '2024-01-15 08:30:00',
                'access_type': 'entry',
                'gate_number': 'Portão 1',
                'driver_name': 'João Silva',
                'carrier_name': 'Transportadora Expresso',
                'security_alert': False
            },
            {
                'vehicle_plate': 'XYZ9W87',
                'timestamp': '2024-01-15 09:15:00',
                'access_type': 'exit',
                'gate_number': 'Portão 2',
                'driver_name': 'Maria Santos',
                'carrier_name': 'Logística Rápida',
                'security_alert': True
            }
        ]
        
        # Gera relatório de acessos
        result = pdf_generator.generate_access_report(
            sample_access_data,
            "data/reports/relatorio_acessos.pdf",
            "Relatório de Acessos - Janeiro 2024",
            "01/01/2024 - 15/01/2024"
        )
        
        print(f"✅ Relatório gerado: {result.file_path}")
        print(f"📄 Páginas: {result.page_count}")
        print(f"📊 Tamanho: {result.file_size} bytes")
        print(f"⏱️  Tempo: {result.generation_time:.2f}s")
        
    except PdfGenerationError as e:
        print(f"❌ Erro na geração do PDF: {e}")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")