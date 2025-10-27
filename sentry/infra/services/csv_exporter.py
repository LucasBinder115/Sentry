# sentry/infra/services/csv_exporter.py

import csv
import os
import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from contextlib import contextmanager
import io

# Configuração de logging
logger = logging.getLogger(__name__)


# Exceções customizadas
class CsvExportError(Exception):
    """Exceção base para erros de exportação CSV."""
    pass


class InvalidDataError(CsvExportError):
    """Exceção para dados inválidos para exportação."""
    pass


class FileSystemError(CsvExportError):
    """Exceção para erros de sistema de arquivos."""
    pass


class CsvExportConfig:
    """Configuração para exportação CSV."""
    
    def __init__(
        self,
        encoding: str = 'utf-8',
        delimiter: str = ',',
        quote_char: str = '"',
        quoting: int = csv.QUOTE_MINIMAL,
        include_timestamp: bool = True,
        include_headers: bool = True,
        max_file_size_mb: int = 100,
        chunk_size: int = 1000
    ):
        self.encoding = encoding
        self.delimiter = delimiter
        self.quote_char = quote_char
        self.quoting = quoting
        self.include_timestamp = include_timestamp
        self.include_headers = include_headers
        self.max_file_size_mb = max_file_size_mb
        self.chunk_size = chunk_size


class CsvExportResult:
    """Resultado da exportação CSV."""
    
    def __init__(
        self,
        file_path: Path,
        row_count: int,
        file_size: int,
        export_time: float,
        headers: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.file_path = file_path
        self.row_count = row_count
        self.file_size = file_size
        self.export_time = export_time
        self.headers = headers
        self.metadata = metadata or {}
    
    def __str__(self) -> str:
        return (f"CsvExportResult(file_path={self.file_path}, "
                f"rows={self.row_count}, size={self.file_size} bytes, "
                f"time={self.export_time:.2f}s)")


class DataPreprocessor:
    """Pré-processador de dados para exportação CSV."""
    
    @staticmethod
    def validate_data(data: List[Dict[str, Any]]) -> None:
        """
        Valida os dados antes da exportação.
        
        Args:
            data: Dados a serem validados
            
        Raises:
            InvalidDataError: Se os dados forem inválidos
        """
        if not data:
            raise InvalidDataError("Nenhum dado fornecido para exportação")
        
        if not isinstance(data, list):
            raise InvalidDataError("Dados devem ser uma lista")
        
        if not all(isinstance(item, dict) for item in data):
            raise InvalidDataError("Todos os itens devem ser dicionários")
        
        # Verifica se há pelo menos uma linha
        if len(data) == 0:
            raise InvalidDataError("Lista de dados vazia")
    
    @staticmethod
    def extract_headers(data: List[Dict[str, Any]]) -> List[str]:
        """
        Extrai cabeçalhos únicos de todos os dicionários.
        
        Args:
            data: Lista de dicionários
            
        Returns:
            Lista de cabeçalhos únicos
        """
        headers = set()
        for item in data:
            headers.update(item.keys())
        return sorted(list(headers))
    
    @staticmethod
    def normalize_value(value: Any) -> str:
        """
        Normaliza valores para formato CSV seguro.
        
        Args:
            value: Valor a ser normalizado
            
        Returns:
            String normalizada
        """
        if value is None:
            return ""
        elif isinstance(value, (int, float, Decimal)):
            return str(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, bool):
            return "Sim" if value else "Não"
        elif isinstance(value, (list, dict)):
            return str(value)  # Ou serializar para JSON se necessário
        else:
            return str(value).strip()
    
    @staticmethod
    def preprocess_data(data: List[Dict[str, Any]], headers: List[str]) -> List[Dict[str, str]]:
        """
        Pré-processa dados para exportação CSV.
        
        Args:
            data: Dados originais
            headers: Cabeçalhos a serem incluídos
            
        Returns:
            Dados pré-processados
        """
        processed_data = []
        
        for row in data:
            processed_row = {}
            for header in headers:
                value = row.get(header)
                processed_row[header] = DataPreprocessor.normalize_value(value)
            processed_data.append(processed_row)
        
        return processed_data


class CsvExporter:
    """
    Serviço robusto para exportação de dados para arquivos CSV.
    
    Oferece:
    - Validação completa de dados
    - Pré-processamento inteligente
    - Exportação em chunks para grandes volumes
    - Suporte a diferentes codificações e formatos
    - Métricas e resultados detalhados
    """
    
    def __init__(self, config: Optional[CsvExportConfig] = None):
        self.config = config or CsvExportConfig()
        self.preprocessor = DataPreprocessor()
        logger.info("CSV Exporter inicializado com configuração: %s", self.config.__dict__)
    
    def export(
        self, 
        data: List[Dict[str, Any]], 
        file_path: Union[str, Path],
        custom_headers: Optional[List[str]] = None
    ) -> CsvExportResult:
        """
        Exporta dados para arquivo CSV.
        
        Args:
            data: Lista de dicionários para exportação
            file_path: Caminho do arquivo de saída
            custom_headers: Cabeçalhos personalizados (opcional)
            
        Returns:
            CsvExportResult: Resultado da exportação
            
        Raises:
            InvalidDataError: Se os dados forem inválidos
            FileSystemError: Se houver erro de arquivo
            CsvExportError: Para outros erros de exportação
        """
        start_time = datetime.now()
        file_path = Path(file_path)
        
        logger.info("Iniciando exportação CSV para: %s", file_path)
        
        try:
            # Validação inicial
            self.preprocessor.validate_data(data)
            self._ensure_output_directory(file_path)
            self._check_file_size_limit(len(data))
            
            # Extrai cabeçalhos
            headers = custom_headers or self.preprocessor.extract_headers(data)
            if not headers:
                raise InvalidDataError("Não foi possível extrair cabeçalhos dos dados")
            
            logger.debug("Exportando %d linhas com %d cabeçalhos", len(data), len(headers))
            
            # Pré-processa dados
            processed_data = self.preprocessor.preprocess_data(data, headers)
            
            # Exporta para arquivo
            row_count = self._write_to_file(processed_data, headers, file_path)
            
            # Calcula métricas
            export_time = (datetime.now() - start_time).total_seconds()
            file_size = file_path.stat().st_size
            
            result = CsvExportResult(
                file_path=file_path,
                row_count=row_count,
                file_size=file_size,
                export_time=export_time,
                headers=headers,
                metadata={
                    'original_row_count': len(data),
                    'headers_count': len(headers),
                    'file_encoding': self.config.encoding,
                    'export_timestamp': datetime.now().isoformat()
                }
            )
            
            logger.info(
                "Exportação CSV concluída: %s (%d linhas, %.2f KB, %.2f segundos)",
                file_path.name, row_count, file_size / 1024, export_time
            )
            
            return result
            
        except (InvalidDataError, FileSystemError, CsvExportError):
            raise
        except Exception as e:
            logger.error("Erro inesperado na exportação CSV: %s", e)
            raise CsvExportError(f"Erro na exportação CSV: {str(e)}") from e
    
    def export_in_chunks(
        self, 
        data: List[Dict[str, Any]], 
        file_path: Union[str, Path],
        custom_headers: Optional[List[str]] = None
    ) -> CsvExportResult:
        """
        Exporta dados em chunks para melhor performance com grandes volumes.
        
        Args:
            data: Lista de dicionários para exportação
            file_path: Caminho do arquivo de saída
            custom_headers: Cabeçalhos personalizados (opcional)
            
        Returns:
            CsvExportResult: Resultado da exportação
        """
        start_time = datetime.now()
        file_path = Path(file_path)
        
        logger.info("Iniciando exportação em chunks para: %s", file_path)
        
        try:
            # Validação inicial
            self.preprocessor.validate_data(data)
            self._ensure_output_directory(file_path)
            
            # Extrai cabeçalhos
            headers = custom_headers or self.preprocessor.extract_headers(data)
            
            total_rows = 0
            
            with self._get_csv_writer(file_path, headers) as writer:
                # Escreve cabeçalhos
                if self.config.include_headers:
                    writer.writerow(headers)
                
                # Processa em chunks
                for i in range(0, len(data), self.config.chunk_size):
                    chunk = data[i:i + self.config.chunk_size]
                    processed_chunk = self.preprocessor.preprocess_data(chunk, headers)
                    
                    for row in processed_chunk:
                        writer.writerow([row.get(header, "") for header in headers])
                        total_rows += 1
                    
                    logger.debug("Processado chunk %d-%d", i, i + len(chunk))
            
            # Calcula métricas
            export_time = (datetime.now() - start_time).total_seconds()
            file_size = file_path.stat().st_size
            
            result = CsvExportResult(
                file_path=file_path,
                row_count=total_rows,
                file_size=file_size,
                export_time=export_time,
                headers=headers,
                metadata={
                    'original_row_count': len(data),
                    'chunk_size': self.config.chunk_size,
                    'total_chunks': (len(data) + self.config.chunk_size - 1) // self.config.chunk_size,
                    'export_method': 'chunked'
                }
            )
            
            logger.info(
                "Exportação em chunks concluída: %s (%d linhas, %.2f KB, %.2f segundos)",
                file_path.name, total_rows, file_size / 1024, export_time
            )
            
            return result
            
        except Exception as e:
            logger.error("Erro na exportação em chunks: %s", e)
            raise CsvExportError(f"Erro na exportação em chunks: {str(e)}") from e
    
    def _write_to_file(
        self, 
        data: List[Dict[str, str]], 
        headers: List[str], 
        file_path: Path
    ) -> int:
        """
        Escreve dados no arquivo CSV.
        
        Args:
            data: Dados pré-processados
            headers: Cabeçalhos
            file_path: Caminho do arquivo
            
        Returns:
            Número de linhas escritas
        """
        row_count = 0
        
        with self._get_csv_writer(file_path, headers) as writer:
            # Escreve cabeçalhos
            if self.config.include_headers:
                writer.writerow(headers)
            
            # Escreve linhas de dados
            for row in data:
                writer.writerow([row.get(header, "") for header in headers])
                row_count += 1
        
        return row_count
    
    @contextmanager
    def _get_csv_writer(self, file_path: Path, headers: List[str]):
        """
        Context manager para criar writer CSV com configurações.
        
        Args:
            file_path: Caminho do arquivo
            headers: Cabeçalhos para validação
        """
        try:
            with open(
                file_path, 
                'w', 
                newline='', 
                encoding=self.config.encoding,
                errors='replace'  # Substitui caracteres problemáticos
            ) as csv_file:
                writer = csv.writer(
                    csv_file,
                    delimiter=self.config.delimiter,
                    quotechar=self.config.quote_char,
                    quoting=self.config.quoting
                )
                yield writer
                
        except IOError as e:
            raise FileSystemError(f"Erro de E/S ao escrever arquivo {file_path}: {str(e)}") from e
        except UnicodeEncodeError as e:
            raise CsvExportError(f"Erro de codificação ao escrever arquivo: {str(e)}") from e
    
    def _ensure_output_directory(self, file_path: Path):
        """Garante que o diretório de saída existe."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise FileSystemError(f"Erro ao criar diretório {file_path.parent}: {str(e)}") from e
    
    def _check_file_size_limit(self, row_count: int):
        """Verifica se a exportação pode exceder o limite de tamanho."""
        # Estimativa conservadora: 1KB por linha
        estimated_size_mb = (row_count * 1024) / (1024 * 1024)
        
        if estimated_size_mb > self.config.max_file_size_mb:
            logger.warning(
                "Exportação estimada em %.2f MB (limite: %d MB)", 
                estimated_size_mb, self.config.max_file_size_mb
            )
    
    def export_to_string(self, data: List[Dict[str, Any]]) -> str:
        """
        Exporta dados para string CSV.
        
        Args:
            data: Dados para exportação
            
        Returns:
            String CSV
        """
        try:
            self.preprocessor.validate_data(data)
            headers = self.preprocessor.extract_headers(data)
            processed_data = self.preprocessor.preprocess_data(data, headers)
            
            output = io.StringIO()
            writer = csv.writer(
                output,
                delimiter=self.config.delimiter,
                quotechar=self.config.quote_char,
                quoting=self.config.quoting
            )
            
            if self.config.include_headers:
                writer.writerow(headers)
            
            for row in processed_data:
                writer.writerow([row.get(header, "") for header in headers])
            
            return output.getvalue()
            
        except Exception as e:
            logger.error("Erro ao exportar para string: %s", e)
            raise CsvExportError(f"Erro na exportação para string: {str(e)}") from e
    
    def get_template(self, headers: List[str]) -> str:
        """
        Gera um template CSV com os cabeçalhos fornecidos.
        
        Args:
            headers: Lista de cabeçalhos
            
        Returns:
            String CSV do template
        """
        if not headers:
            raise InvalidDataError("Lista de cabeçalhos vazia")
        
        output = io.StringIO()
        writer = csv.writer(
            output,
            delimiter=self.config.delimiter,
            quotechar=self.config.quote_char,
            quoting=csv.QUOTE_ALL  # Quote todos para template
        )
        
        writer.writerow(headers)
        # Linha de exemplo com valores vazios
        writer.writerow([""] * len(headers))
        
        return output.getvalue()


# Fábrica para criação de exportadores
class CsvExporterFactory:
    """Fábrica para criar instâncias de CsvExporter com configurações comuns."""
    
    @staticmethod
    def create_default_exporter() -> CsvExporter:
        """Cria exportador com configurações padrão."""
        return CsvExporter()
    
    @staticmethod
    def create_european_exporter() -> CsvExporter:
        """Cria exportador com configurações europeias (ponto e vírgula)."""
        config = CsvExportConfig(delimiter=';', quote_char='"', quoting=csv.QUOTE_ALL)
        return CsvExporter(config)
    
    @staticmethod
    def create_tab_delimited_exporter() -> CsvExporter:
        """Cria exportador com tabulação como delimitador."""
        config = CsvExportConfig(delimiter='\t', quote_char='"', quoting=csv.QUOTE_MINIMAL)
        return CsvExporter(config)
    
    @staticmethod
    def create_large_file_exporter() -> CsvExporter:
        """Cria exportador otimizado para arquivos grandes."""
        config = CsvExportConfig(chunk_size=5000, max_file_size_mb=500)
        return CsvExporter(config)


# Exemplo de uso
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Dados de exemplo
        sample_data = [
            {
                'id': 1,
                'nome': 'João Silva',
                'email': 'joao@email.com',
                'data_criacao': datetime.now(),
                'ativo': True,
                'saldo': Decimal('1500.50')
            },
            {
                'id': 2,
                'nome': 'Maria Santos',
                'email': 'maria@email.com',
                'data_criacao': datetime.now(),
                'ativo': False,
                'saldo': Decimal('2300.75')
            },
            {
                'id': 3,
                'nome': 'Pedro Oliveira',
                'email': 'pedro@email.com',
                'data_criacao': datetime.now(),
                'ativo': True,
                'saldo': None  # Teste com valor nulo
            }
        ]
        
        # Cria exportador
        exporter = CsvExporterFactory.create_default_exporter()
        
        # Exporta para arquivo
        result = exporter.export(sample_data, "data/exports/usuarios.csv")
        print(f"✅ Exportação concluída: {result}")
        
        # Exporta para string
        csv_string = exporter.export_to_string(sample_data)
        print(f"\n📄 CSV como string:\n{csv_string}")
        
        # Gera template
        template = exporter.get_template(['id', 'nome', 'email', 'telefone'])
        print(f"\n📋 Template CSV:\n{template}")
        
    except CsvExportError as e:
        print(f"❌ Erro na exportação: {e}")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")