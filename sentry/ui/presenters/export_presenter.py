# sentry/ui/presenters/export_presenter.py

import os
from datetime import datetime
from typing import Dict, List, Optional, Any

# ====================================================================
# Imports com Fallbacks Robustos
# ====================================================================
try:
    from sentry.core.use_cases.export_records import ExportRecordsUseCase
except ImportError:
    # Fallback para desenvolvimento
    class ExportRecordsUseCase:
        def __init__(self, movement_repo, csv_exporter, pdf_generator):
            self.movement_repo = movement_repo
            self.csv_exporter = csv_exporter
            self.pdf_generator = pdf_generator
        
        def execute(self, params):
            # Implementação básica para desenvolvimento
            return "/tmp/export_fallback.pdf"

try:
    from sentry.infra.services.csv_exporter import CsvExporter
except ImportError:
    class CsvExporter:
        def export(self, data, file_path):
            # Fallback simples para CSV
            with open(file_path, 'w') as f:
                f.write("Fallback CSV Export\n")
            return file_path

try:
    from sentry.infra.services.pdf_generator import PdfGenerator
except ImportError:
    class PdfGenerator:
        def generate(self, data, file_path):
            # Fallback simples para PDF
            with open(file_path, 'w') as f:
                f.write("Fallback PDF Export\n")
            return file_path

try:
    from sentry.infra.database.repositories.vehicle_movement_repo import VehicleMovementRepository
except ImportError:
    class VehicleMovementRepository:
        def find_with_filters(self, filters):
            # Retorna dados mock para desenvolvimento
            return [
                {"id": 1, "plate": "ABC1234", "timestamp": "2024-01-01", "type": "ENTRY"},
                {"id": 2, "plate": "XYZ5678", "timestamp": "2024-01-01", "type": "EXIT"}
            ]


class ExportPresenter:
    """
    Presenter para exportação de registros.
    Gerencia a comunicação entre a view de exportação e os casos de uso.
    """
    
    # Formatos de exportação suportados
    SUPPORTED_FORMATS = ['csv', 'pdf', 'xlsx', 'json']
    
    # Filtros padrão disponíveis
    DEFAULT_FILTERS = {
        'date_range': None,
        'plate': None,
        'access_type': None,
        'carrier': None,
        'status': None
    }

    def __init__(self, view):
        self.view = view
        self._initialize_dependencies()
        self._setup_export_handlers()
        
        # Estado da exportação
        self.current_export = None
        self.export_history = []
        self.export_config = self._load_export_config()

    def _initialize_dependencies(self):
        """Inicializa dependências com tratamento robusto de erros."""
        try:
            self.movement_repo = VehicleMovementRepository()
            self.csv_exporter = CsvExporter()
            self.pdf_generator = PdfGenerator()
            self.export_use_case = ExportRecordsUseCase(
                self.movement_repo, 
                self.csv_exporter, 
                self.pdf_generator
            )
        except Exception as e:
            self._handle_dependency_error(e)

    def _handle_dependency_error(self, error):
        """Trata erros de inicialização de dependências."""
        error_msg = f"Erro na inicialização: {error}"
        print(f"AVISO: {error_msg}")
        
        # Cria instâncias fallback
        self.movement_repo = VehicleMovementRepository()
        self.csv_exporter = CsvExporter()
        self.pdf_generator = PdfGenerator()
        self.export_use_case = ExportRecordsUseCase(
            self.movement_repo, 
            self.csv_exporter, 
            self.pdf_generator
        )
        
        self.view.show_warning("Algumas funcionalidades de exportação podem estar limitadas")

    def _setup_export_handlers(self):
        """Configura handlers para eventos de exportação."""
        # Pode ser expandido para callbacks de progresso, etc.
        self.export_handlers = {
            'on_progress': None,
            'on_complete': None,
            'on_error': None
        }

    def _load_export_config(self):
        """Carrega configurações de exportação."""
        return {
            'default_format': 'pdf',
            'default_directory': self._get_default_export_dir(),
            'include_timestamp': True,
            'max_file_size': 100 * 1024 * 1024,  # 100MB
            'allowed_formats': self.SUPPORTED_FORMATS
        }

    def _get_default_export_dir(self):
        """Obtém diretório padrão para exportação."""
        default_dirs = [
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Documents"),
            os.path.abspath("./exports")
        ]
        
        for directory in default_dirs:
            if os.path.exists(directory) and os.path.isdir(directory):
                return directory
        
        # Fallback: diretório temporário
        return "/tmp"

    # ====================================================================
    # MÉTODOS PRINCIPAIS DE EXPORTAÇÃO
    # ====================================================================

    def export_records(self, params: Dict[str, Any]):
        """
        Exporta registros baseado nos parâmetros fornecidos.
        
        Args:
            params: Dicionário com parâmetros de exportação
                - format: formato de exportação (csv, pdf, etc.)
                - filters: filtros para os dados
                - filename: nome do arquivo (opcional)
                - include_headers: incluir cabeçalhos (padrão: True)
        """
        try:
            # Valida parâmetros básicos
            self._validate_export_params(params)
            
            # Prepara parâmetros com valores padrão
            processed_params = self._prepare_export_params(params)
            
            # Notifica início da exportação
            self.view.set_export_loading(True)
            self.view.show_info("Iniciando exportação...")
            
            # Executa a exportação
            file_path = self.export_use_case.execute(processed_params)
            
            # Processa resultado
            self._handle_export_success(file_path, processed_params)
            
        except ValueError as e:
            self._handle_export_error(f"Parâmetros inválidos: {e}")
        except PermissionError as e:
            self._handle_export_error(f"Sem permissão para salvar arquivo: {e}")
        except IOError as e:
            self._handle_export_error(f"Erro de E/S durante exportação: {e}")
        except Exception as e:
            self._handle_export_error(f"Erro inesperado durante exportação: {e}")
        finally:
            self.view.set_export_loading(False)

    def _validate_export_params(self, params: Dict[str, Any]):
        """Valida os parâmetros de exportação."""
        if not params:
            raise ValueError("Parâmetros de exportação não fornecidos")
        
        # Valida formato
        export_format = params.get('format', self.export_config['default_format'])
        if export_format not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Formato '{export_format}' não suportado. Use: {', '.join(self.SUPPORTED_FORMATS)}")
        
        # Valida filtros básicos
        filters = params.get('filters', {})
        if not isinstance(filters, dict):
            raise ValueError("Filtros devem ser um dicionário")

    def _prepare_export_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara e enriquece os parâmetros de exportação."""
        processed_params = params.copy()
        
        # Define formato padrão se não especificado
        if 'format' not in processed_params:
            processed_params['format'] = self.export_config['default_format']
        
        # Gera nome de arquivo se não fornecido
        if 'filename' not in processed_params:
            processed_params['filename'] = self._generate_filename(processed_params)
        
        # Define diretório de exportação
        if 'directory' not in processed_params:
            processed_params['directory'] = self.export_config['default_directory']
        
        # Garante que include_headers seja booleano
        if 'include_headers' not in processed_params:
            processed_params['include_headers'] = True
        
        return processed_params

    def _generate_filename(self, params: Dict[str, Any]) -> str:
        """Gera nome de arquivo para exportação."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        format_extension = params.get('format', 'pdf')
        
        base_name = "registros_veiculos"
        
        # Adiciona informações dos filtros ao nome do arquivo
        filters = params.get('filters', {})
        if filters.get('plate'):
            base_name += f"_{filters['plate']}"
        if filters.get('date_range'):
            base_name += f"_{filters['date_range'][0].replace('-', '')}"
        
        return f"{base_name}_{timestamp}.{format_extension}"

    def _handle_export_success(self, file_path: str, params: Dict[str, Any]):
        """Processa exportação bem-sucedida."""
        # Verifica se arquivo foi criado
        if not os.path.exists(file_path):
            raise IOError(f"Arquivo de exportação não foi criado: {file_path}")
        
        # Obtém informações do arquivo
        file_size = os.path.getsize(file_path)
        file_info = {
            'path': file_path,
            'size': file_size,
            'format': params.get('format'),
            'timestamp': datetime.now(),
            'filters': params.get('filters', {})
        }
        
        # Adiciona ao histórico
        self.export_history.append(file_info)
        
        # Limita histórico aos 50 mais recentes
        if len(self.export_history) > 50:
            self.export_history = self.export_history[-50:]
        
        # Notifica view
        success_msg = self._format_success_message(file_info)
        self.view.show_success(success_msg)
        
        # Chama callback de sucesso se definido
        if self.export_handlers['on_complete']:
            self.export_handlers['on_complete'](file_info)

    def _handle_export_error(self, error_message: str):
        """Processa erro durante exportação."""
        error_info = {
            'message': error_message,
            'timestamp': datetime.now(),
            'type': 'export_error'
        }
        
        # Log do erro
        print(f"ERRO DE EXPORTAÇÃO: {error_message}")
        
        # Notifica view
        self.view.show_error(error_message)
        
        # Chama callback de erro se definido
        if self.export_handlers['on_error']:
            self.export_handlers['on_error'](error_info)

    def _format_success_message(self, file_info: Dict[str, Any]) -> str:
        """Formata mensagem de sucesso para exibição."""
        file_size_kb = file_info['size'] / 1024
        format_name = file_info['format'].upper()
        
        message = f"""
✅ Exportação concluída com sucesso!

📊 Formato: {format_name}
💾 Tamanho: {file_size_kb:.2f} KB
📁 Local: {file_info['path']}

O arquivo está pronto para uso.
        """
        
        return message.strip()

    # ====================================================================
    # MÉTODOS AVANÇADOS DE EXPORTAÇÃO
    # ====================================================================

    def export_with_template(self, template_name: str, params: Dict[str, Any]):
        """Exporta usando um template pré-definido."""
        try:
            # Carrega template
            template = self._load_export_template(template_name)
            if not template:
                raise ValueError(f"Template '{template_name}' não encontrado")
            
            # Combina parâmetros do template com os fornecidos
            merged_params = {**template, **params}
            
            # Executa exportação
            self.export_records(merged_params)
            
        except Exception as e:
            self._handle_export_error(f"Erro ao exportar com template: {e}")

    def batch_export(self, export_list: List[Dict[str, Any]]):
        """Executa múltiplas exportações em lote."""
        results = {
            'successful': [],
            'failed': []
        }
        
        total = len(export_list)
        
        for index, export_params in enumerate(export_list, 1):
            try:
                self.view.show_info(f"Processando {index} de {total}...")
                
                file_path = self.export_use_case.execute(export_params)
                results['successful'].append({
                    'params': export_params,
                    'file_path': file_path
                })
                
            except Exception as e:
                results['failed'].append({
                    'params': export_params,
                    'error': str(e)
                })
        
        # Relatório final
        self._show_batch_report(results)

    def _load_export_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Carrega template de exportação pré-definido."""
        templates = {
            'daily_report': {
                'format': 'pdf',
                'filters': {'date_range': [datetime.now().date(), datetime.now().date()]},
                'filename': f"relatorio_diario_{datetime.now().strftime('%Y%m%d')}.pdf"
            },
            'monthly_summary': {
                'format': 'csv',
                'filters': {'group_by': 'month'},
                'include_headers': True
            },
            'security_audit': {
                'format': 'pdf',
                'filters': {'status': 'SECURITY_INCIDENT'},
                'filename': 'auditoria_seguranca.pdf'
            }
        }
        
        return templates.get(template_name)

    def _show_batch_report(self, results: Dict[str, List]):
        """Exibe relatório de exportação em lote."""
        successful_count = len(results['successful'])
        failed_count = len(results['failed'])
        
        report_message = f"""
📊 Relatório de Exportação em Lote:

✅ Sucessos: {successful_count}
❌ Falhas: {failed_count}
📋 Total: {successful_count + failed_count}
        """
        
        if failed_count > 0:
            report_message += f"\n⚠️ {failed_count} exportação(ões) falharam. Verifique os logs."
        
        self.view.show_info(report_message.strip())

    # ====================================================================
    # MÉTODOS UTILITÁRIOS
    # ====================================================================

    def get_export_history(self) -> List[Dict[str, Any]]:
        """Retorna histórico de exportações."""
        return self.export_history.copy()

    def clear_export_history(self):
        """Limpa histórico de exportações."""
        self.export_history.clear()
        self.view.show_info("Histórico de exportações limpo")

    def get_supported_formats(self) -> List[str]:
        """Retorna lista de formatos suportados."""
        return self.SUPPORTED_FORMATS.copy()

    def validate_export_directory(self, directory: str) -> bool:
        """Valida se o diretório pode ser usado para exportação."""
        try:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            # Testa escrita
            test_file = os.path.join(directory, 'test_write.tmp')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            
            return True
            
        except Exception:
            return False

    def set_export_handlers(self, handlers: Dict[str, callable]):
        """Configura callbacks para eventos de exportação."""
        self.export_handlers.update(handlers)

    def get_export_config(self) -> Dict[str, Any]:
        """Retorna configuração atual de exportação."""
        return self.export_config.copy()

    def update_export_config(self, new_config: Dict[str, Any]):
        """Atualiza configuração de exportação."""
        self.export_config.update(new_config)
        self.view.show_info("Configuração de exportação atualizada")


# ====================================================================
# CLASSE PARA TESTES E DESENVOLVIMENTO
# ====================================================================

class MockExportView:
    """View mock para testes do ExportPresenter."""
    
    def __init__(self):
        self.messages = []
        self.loading_state = False
    
    def show_success(self, message):
        self.messages.append(('success', message))
        print(f"✅ {message}")
    
    def show_error(self, message):
        self.messages.append(('error', message))
        print(f"❌ {message}")
    
    def show_info(self, message):
        self.messages.append(('info', message))
        print(f"ℹ️ {message}")
    
    def show_warning(self, message):
        self.messages.append(('warning', message))
        print(f"⚠️ {message}")
    
    def set_export_loading(self, loading):
        self.loading_state = loading
        print(f"Loading: {loading}")


# Exemplo de uso para testes
if __name__ == "__main__":
    view = MockExportView()
    presenter = ExportPresenter(view)
    
    # Teste de exportação básica
    test_params = {
        'format': 'pdf',
        'filters': {'plate': 'ABC1234'},
        'filename': 'test_export.pdf'
    }
    
    presenter.export_records(test_params)
    print("Histórico:", presenter.get_export_history())