# sentry/core/use_cases/export_records.py

import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass

# Configuração de logging
logger = logging.getLogger(__name__)


# Exceções customizadas
class ExportError(Exception):
    """Exceção base para erros de exportação."""
    pass


class InvalidExportParametersError(ExportError):
    """Exceção para parâmetros de exportação inválidos."""
    pass


class NoDataFoundError(ExportError):
    """Exceção quando não há dados para exportar."""
    pass


class UnsupportedFileTypeError(ExportError):
    """Exceção para tipo de arquivo não suportado."""
    pass


class StorageError(ExportError):
    """Exceção para erros de armazenamento."""
    pass


@dataclass
class ExportParams:
    """Parâmetros estruturados para exportação."""
    file_type: str
    date_start: str
    date_end: str
    filters: Optional[Dict[str, Any]] = None
    user_id: Optional[int] = None


@dataclass
class ExportResult:
    """Resultado estruturado da exportação."""
    file_path: str
    file_size: int
    record_count: int
    export_time: datetime
    metadata: Dict[str, Any]


class FileExporter(ABC):
    """Interface para exportadores de arquivo."""
    
    @abstractmethod
    def export(self, records: List[Any], output_path: str) -> None:
        """Exporta registros para o formato específico."""
        pass
    
    @abstractmethod
    def supports_format(self, file_type: str) -> bool:
        """Verifica se o exportador suporta o formato."""
        pass


class ExportValidator:
    """Validador para parâmetros de exportação."""
    
    SUPPORTED_FORMATS = {"csv", "pdf", "xlsx", "json"}
    MAX_RECORDS = 100000  # Limite máximo de registros para evitar sobrecarga
    
    @classmethod
    def validate_params(cls, params: Dict[str, Any]) -> ExportParams:
        """
        Valida e normaliza os parâmetros de exportação.
        
        Args:
            params: Dicionário com parâmetros de exportação
            
        Returns:
            ExportParams: Parâmetros validados e estruturados
            
        Raises:
            InvalidExportParametersError: Se os parâmetros forem inválidos
        """
        file_type = params.get("file_type", "").lower().strip()
        date_start = params.get("date_start", "").strip()
        date_end = params.get("date_end", "").strip()
        
        # Validações básicas
        if not all([file_type, date_start, date_end]):
            raise InvalidExportParametersError(
                "Parâmetros obrigatórios: file_type, date_start, date_end"
            )
        
        # Valida formato do arquivo
        if file_type not in cls.SUPPORTED_FORMATS:
            raise InvalidExportParametersError(
                f"Tipo de arquivo '{file_type}' não suportado. "
                f"Formatos suportados: {', '.join(cls.SUPPORTED_FORMATS)}"
            )
        
        # Valida formato das datas (exemplo básico)
        try:
            datetime.strptime(date_start, "%Y-%m-%d")
            datetime.strptime(date_end, "%Y-%m-%d")
        except ValueError:
            raise InvalidExportParametersError(
                "Formato de data inválido. Use YYYY-MM-DD."
            )
        
        # Valida que data final não é anterior à data inicial
        if date_start > date_end:
            raise InvalidExportParametersError(
                "Data final não pode ser anterior à data inicial."
            )
        
        return ExportParams(
            file_type=file_type,
            date_start=date_start,
            date_end=date_end,
            filters=params.get("filters"),
            user_id=params.get("user_id")
        )


class ExportDirectoryManager:
    """Gerenciador de diretórios para exportação."""
    
    def __init__(self, base_export_dir: str = "data/exports"):
        self.base_export_dir = Path(base_export_dir)
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Garante que os diretórios de exportação existam."""
        try:
            self.base_export_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise StorageError(f"Erro ao criar diretório de exportação: {e}")
    
    def generate_file_path(self, file_type: str, prefix: str = "export") -> str:
        """
        Gera caminho único para arquivo de exportação.
        
        Args:
            file_type: Tipo do arquivo
            prefix: Prefixo do nome do arquivo
            
        Returns:
            Caminho completo do arquivo
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.{file_type}"
        return str(self.base_export_dir / filename)
    
    def get_file_size(self, file_path: str) -> int:
        """
        Obtém tamanho do arquivo em bytes.
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            Tamanho em bytes
        """
        try:
            return Path(file_path).stat().st_size
        except Exception as e:
            raise StorageError(f"Erro ao obter tamanho do arquivo: {e}")


class ExportRecordsUseCase:
    """
    Caso de uso para exportação de registros.
    
    Responsável por orquestrar o processo de exportação:
    - Validação de parâmetros
    - Busca de dados
    - Geração de arquivo
    - Retorno de metadados
    """
    
    def __init__(
        self, 
        movement_repository, 
        exporters: List[FileExporter],
        export_dir_manager: Optional[ExportDirectoryManager] = None
    ):
        self.movement_repo = movement_repository
        self.exporters = {exporter.supports_format: exporter for exporter in exporters}
        self.dir_manager = export_dir_manager or ExportDirectoryManager()
        self.validator = ExportValidator()
    
    def execute(self, params: Dict[str, Any]) -> ExportResult:
        """
        Executa o processo de exportação.
        
        Args:
            params: Parâmetros de exportação
            
        Returns:
            ExportResult: Resultado da exportação com metadados
            
        Raises:
            ExportError: Em caso de erro durante a exportação
        """
        logger.info(
            "Iniciando exportação - Tipo: %s, Período: %s a %s",
            params.get("file_type"),
            params.get("date_start"),
            params.get("date_end")
        )
        
        try:
            # 1. Validação de parâmetros
            export_params = self.validator.validate_params(params)
            
            # 2. Buscar dados no repositório
            records = self._fetch_records(export_params)
            
            # 3. Gerar caminho do arquivo
            output_path = self.dir_manager.generate_file_path(export_params.file_type)
            
            # 4. Executar exportação
            self._perform_export(records, export_params.file_type, output_path)
            
            # 5. Coletar metadados
            return self._create_export_result(
                output_path, records, export_params
            )
            
        except (InvalidExportParametersError, NoDataFoundError, UnsupportedFileTypeError):
            # Re-lança exceções específicas
            raise
        except Exception as e:
            logger.error("Erro durante exportação: %s", str(e))
            raise ExportError(f"Falha na exportação: {str(e)}")
    
    def _fetch_records(self, params: ExportParams) -> List[Any]:
        """
        Busca registros com base nos parâmetros.
        
        Args:
            params: Parâmetros de exportação
            
        Returns:
            Lista de registros
            
        Raises:
            NoDataFoundError: Se não houver registros
        """
        try:
            records = self.movement_repo.find_by_date_range(
                params.date_start,
                params.date_end,
                filters=params.filters
            )
            
            if not records:
                raise NoDataFoundError(
                    f"Nenhum registro encontrado para o período "
                    f"{params.date_start} a {params.date_end}"
                )
            
            # Verifica limite máximo de registros
            if len(records) > self.validator.MAX_RECORDS:
                logger.warning(
                    "Exportação com muitos registros: %d (limite: %d)",
                    len(records), self.validator.MAX_RECORDS
                )
            
            logger.info("Encontrados %d registros para exportação", len(records))
            return records
            
        except Exception as e:
            logger.error("Erro ao buscar registros: %s", str(e))
            raise ExportError(f"Erro na busca de dados: {str(e)}")
    
    def _perform_export(self, records: List[Any], file_type: str, output_path: str) -> None:
        """
        Executa a exportação usando o exportador apropriado.
        
        Args:
            records: Registros a serem exportados
            file_type: Tipo de arquivo
            output_path: Caminho de saída
            
        Raises:
            UnsupportedFileTypeError: Se o tipo não for suportado
        """
        exporter = self.exporters.get(file_type)
        if not exporter:
            raise UnsupportedFileTypeError(
                f"Exportador para tipo '{file_type}' não encontrado"
            )
        
        try:
            logger.info("Iniciando exportação para: %s", output_path)
            exporter.export(records, output_path)
            logger.info("Exportação concluída: %s", output_path)
            
        except Exception as e:
            logger.error("Erro durante exportação para %s: %s", file_type, str(e))
            # Tenta limpar arquivo corrompido
            self._cleanup_failed_export(output_path)
            raise ExportError(f"Erro na geração do arquivo {file_type}: {str(e)}")
    
    def _cleanup_failed_export(self, file_path: str) -> None:
        """Remove arquivo em caso de falha na exportação."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info("Arquivo corrompido removido: %s", file_path)
        except Exception as e:
            logger.warning("Erro ao remover arquivo corrompido: %s", str(e))
    
    def _create_export_result(
        self, 
        file_path: str, 
        records: List[Any], 
        params: ExportParams
    ) -> ExportResult:
        """
        Cria resultado estruturado da exportação.
        
        Args:
            file_path: Caminho do arquivo
            records: Registros exportados
            params: Parâmetros de exportação
            
        Returns:
            ExportResult com metadados
        """
        try:
            file_size = self.dir_manager.get_file_size(file_path)
        except StorageError as e:
            logger.warning("Não foi possível obter tamanho do arquivo: %s", str(e))
            file_size = 0
        
        return ExportResult(
            file_path=file_path,
            file_size=file_size,
            record_count=len(records),
            export_time=datetime.now(),
            metadata={
                "file_type": params.file_type,
                "date_range": {
                    "start": params.date_start,
                    "end": params.date_end
                },
                "filters": params.filters,
                "user_id": params.user_id
            }
        )


# Implementações de exemplo para os exportadores
class CSVExporter(FileExporter):
    """Exportador para formato CSV."""
    
    def export(self, records: List[Any], output_path: str) -> None:
        # Implementação real de exportação CSV
        # Exemplo simplificado
        import csv
        
        if not records:
            raise ValueError("Nenhum registro para exportar")
        
        # Aqui você converteria os registros para o formato CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Implementar lógica de escrita baseada na estrutura dos registros
            pass
    
    def supports_format(self, file_type: str) -> bool:
        return file_type == "csv"


class PDFExporter(FileExporter):
    """Exportador para formato PDF."""
    
    def export(self, records: List[Any], output_path: str) -> None:
        # Implementação real de geração de PDF
        # Exemplo simplificado
        from reportlab.pdfgen import canvas
        
        c = canvas.Canvas(output_path)
        # Implementar lógica de geração do PDF
        c.save()
    
    def supports_format(self, file_type: str) -> bool:
        return file_type == "pdf"


# Exemplo de uso
if __name__ == "__main__":
    # Configuração básica de logging
    logging.basicConfig(level=logging.INFO)
    
    # Exemplo de uso (em produção, usar injeção de dependência)
    exporters = [CSVExporter(), PDFExporter()]
    use_case = ExportRecordsUseCase(
        movement_repository=...,  # Repositório real
        exporters=exporters
    )
    
    try:
        params = {
            "file_type": "csv",
            "date_start": "2024-01-01",
            "date_end": "2024-01-31",
            "filters": {"status": "completed"},
            "user_id": 123
        }
        
        result = use_case.execute(params)
        print(f"Exportação concluída: {result.file_path}")
        print(f"Registros exportados: {result.record_count}")
        print(f"Tamanho do arquivo: {result.file_size} bytes")
        
    except ExportError as e:
        print(f"Erro na exportação: {e}")