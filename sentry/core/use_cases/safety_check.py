# sentry/core/use_cases/safety_check.py

import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from sentry.infra.services.api_adapters_old import NHTSAAPIAdapter

# Configuração de logging
logger = logging.getLogger(__name__)


# Exceções customizadas
class SafetyCheckError(Exception):
    """Exceção base para erros de verificação de segurança."""
    pass


class InvalidVINError(SafetyCheckError):
    """Exceção para VIN inválido."""
    pass


class APIServiceError(SafetyCheckError):
    """Exceção para erros na comunicação com a API."""
    pass


class SafetyCheckTimeoutError(SafetyCheckError):
    """Exceção para timeout na verificação de segurança."""
    pass


class RecallSeverity(Enum):
    """Níveis de severidade de recall."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass
class RecallInfo:
    """Informações estruturadas sobre um recall."""
    recall_id: str
    description: str
    severity: RecallSeverity
    date_reported: Optional[datetime]
    components: List[str]
    consequence: Optional[str]
    remedy: Optional[str]
    manufacturer: Optional[str]
    campaign_number: Optional[str]
    nhtsa_url: Optional[str]


@dataclass
class SafetyCheckResult:
    """Resultado completo da verificação de segurança."""
    vin: str
    status: str
    recall_count: int
    recalls: List[RecallInfo]
    check_timestamp: datetime
    vehicle_info: Optional[Dict[str, Any]]
    metadata: Dict[str, Any]


class VINValidator:
    """Validador para números de identificação de veículos (VIN)."""
    
    VIN_PATTERN = re.compile(r'^[A-HJ-NPR-Z0-9]{17}$')  # VIN padrão de 17 caracteres
    FORBIDDEN_CHARS = {'I', 'O', 'Q'}  # Caracteres proibidos no VIN
    
    @classmethod
    def validate_vin(cls, vin: str) -> str:
        """
        Valida o formato do VIN.
        
        Args:
            vin: VIN a ser validado
            
        Returns:
            VIN limpo e validado
            
        Raises:
            InvalidVINError: Se o VIN for inválido
        """
        if not vin or not isinstance(vin, str):
            raise InvalidVINError("VIN não pode estar vazio")
        
        cleaned_vin = vin.strip().upper()
        
        # Verifica comprimento
        if len(cleaned_vin) != 17:
            raise InvalidVINError("VIN deve ter exatamente 17 caracteres")
        
        # Verifica caracteres proibidos
        for char in cls.FORBIDDEN_CHARS:
            if char in cleaned_vin:
                raise InvalidVINError(f"VIN contém caractere proibido: {char}")
        
        # Verifica padrão
        if not cls.VIN_PATTERN.match(cleaned_vin):
            raise InvalidVINError("Formato de VIN inválido")
        
        # Verifica checksum (opcional - validação mais avançada)
        if not cls._validate_vin_checksum(cleaned_vin):
            logger.warning("VIN pode ter checksum inválido: %s", cleaned_vin)
        
        return cleaned_vin
    
    @staticmethod
    def _validate_vin_checksum(vin: str) -> bool:
        """
        Valida checksum do VIN (implementação básica).
        
        Args:
            vin: VIN a ser validado
            
        Returns:
            True se checksum é válido (ou validação ignorada)
        """
        # Implementação simplificada - em produção, usar algoritmo completo
        # que considera pesos e posições específicas
        try:
            # Alguma validação básica pode ser adicionada aqui
            return True  # Por enquanto, aceita todos os VINs que passaram na validação básica
        except Exception:
            return False
    
    @classmethod
    def extract_vin_info(cls, vin: str) -> Dict[str, str]:
        """
        Extrai informações básicas do VIN.
        
        Args:
            vin: VIN validado
            
        Returns:
            Dicionário com informações extraídas
        """
        try:
            # WMI (World Manufacturer Identifier) - primeiros 3 caracteres
            wmi = vin[:3]
            
            # VDS (Vehicle Descriptor Section) - caracteres 4 a 9
            vds = vin[3:9]
            
            # VIS (Vehicle Identifier Section) - últimos 8 caracteres
            vis = vin[9:]
            
            # Ano do modelo (caractere 10)
            year_code = vin[9]
            model_year = cls._decode_model_year(year_code)
            
            # Planta de montagem (caractere 11)
            plant_code = vin[10]
            
            return {
                'wmi': wmi,
                'vds': vds,
                'vis': vis,
                'model_year': model_year,
                'plant_code': plant_code,
                'manufacturer_region': cls._decode_manufacturer_region(wmi[0])
            }
        except Exception as e:
            logger.warning("Erro ao extrair informações do VIN %s: %s", vin, e)
            return {}
    
    @staticmethod
    def _decode_model_year(year_code: str) -> str:
        """Decodifica o código do ano do modelo."""
        # Mapeamento simplificado - em produção, usar tabela completa
        year_map = {
            'A': '2010', 'B': '2011', 'C': '2012', 'D': '2013', 'E': '2014',
            'F': '2015', 'G': '2016', 'H': '2017', 'J': '2018', 'K': '2019',
            'L': '2020', 'M': '2021', 'N': '2022', 'P': '2023', 'R': '2024',
            'S': '2025', 'T': '2026', 'V': '2027', 'W': '2028', 'X': '2029',
            'Y': '2030', '1': '2031', '2': '2032', '3': '2033', '4': '2034',
            '5': '2035', '6': '2036', '7': '2037', '8': '2038', '9': '2039'
        }
        return year_map.get(year_code, 'Desconhecido')
    
    @staticmethod
    def _decode_manufacturer_region(region_code: str) -> str:
        """Decodifica a região do fabricante."""
        region_map = {
            '1': 'América do Norte',
            '2': 'América do Norte',
            '3': 'América do Norte',
            '4': 'América do Norte',
            '5': 'América do Norte',
            '6': 'Oceania',
            '7': 'Oceania',
            '8': 'América do Sul',
            '9': 'América do Sul',
            'A': 'África',
            'B': 'África',
            'C': 'África',
            'D': 'África',
            'E': 'África',
            'F': 'África',
            'G': 'África',
            'H': 'África',
            'J': 'Ásia',
            'K': 'Ásia',
            'L': 'Ásia',
            'M': 'Ásia',
            'N': 'Ásia',
            'P': 'Ásia',
            'R': 'Ásia',
            'S': 'Europa',
            'T': 'Europa',
            'U': 'Europa',
            'V': 'Europa',
            'W': 'Europa',
            'X': 'Europa',
            'Y': 'Europa',
            'Z': 'Europa'
        }
        return region_map.get(region_code, 'Desconhecida')


class RecallDataProcessor:
    """Processador para dados de recall da API."""
    
    @staticmethod
    def determine_severity(recall_data: Dict[str, Any]) -> RecallSeverity:
        """
        Determina a severidade do recall baseado nos dados.
        
        Args:
            recall_data: Dados brutos do recall
            
        Returns:
            Nível de severidade
        """
        description = recall_data.get('Description', '').lower()
        consequence = recall_data.get('Conequence', '').lower()
        
        # Palavras-chave para alta severidade
        high_severity_keywords = [
            'incendio', 'fogo', 'fire', 'incêndio',
            'freio', 'brake', 'direção', 'steering',
            'airbag', 'srs', 'cinto', 'seatbelt',
            'motor', 'engine', 'parada', 'stall',
            'contaminação', 'contamination'
        ]
        
        # Palavras-chave para média severidade
        medium_severity_keywords = [
            'elétrico', 'electrical', 'bateria', 'battery',
            'combustível', 'fuel', 'vazamento', 'leak',
            'iluminação', 'lighting', 'farol', 'headlight'
        ]
        
        text_to_check = f"{description} {consequence}"
        
        for keyword in high_severity_keywords:
            if keyword in text_to_check:
                return RecallSeverity.HIGH
        
        for keyword in medium_severity_keywords:
            if keyword in text_to_check:
                return RecallSeverity.MEDIUM
        
        return RecallSeverity.UNKNOWN
    
    @classmethod
    def parse_recall_date(cls, date_str: Optional[str]) -> Optional[datetime]:
        """
        Parse da data do recall.
        
        Args:
            date_str: String da data
            
        Returns:
            Objeto datetime ou None
        """
        if not date_str:
            return None
        
        try:
            # Tenta vários formatos de data
            formats = [
                '%Y-%m-%d',
                '%m/%d/%Y',
                '%d/%m/%Y',
                '%Y%m%d'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            logger.warning("Não foi possível parsear a data: %s", date_str)
            return None
            
        except Exception as e:
            logger.warning("Erro ao parsear data %s: %s", date_str, e)
            return None
    
    @classmethod
    def process_recall_data(cls, recall_data: Dict[str, Any]) -> RecallInfo:
        """
        Processa dados brutos do recall para estrutura padronizada.
        
        Args:
            recall_data: Dados brutos da API
            
        Returns:
            RecallInfo estruturado
        """
        # Extrai componentes afetados
        components = []
        component_name = recall_data.get('Component', '')
        if component_name:
            components = [comp.strip() for comp in component_name.split(',')]
        
        return RecallInfo(
            recall_id=recall_data.get('RecallId', ''),
            description=recall_data.get('Description', ''),
            severity=cls.determine_severity(recall_data),
            date_reported=cls.parse_recall_date(recall_data.get('ReportReceivedDate')),
            components=components,
            consequence=recall_data.get('Conequence', ''),
            remedy=recall_data.get('Remedy', ''),
            manufacturer=recall_data.get('Manufacturer', ''),
            campaign_number=recall_data.get('NHTSACampaignNumber', ''),
            nhtsa_url=recall_data.get('URL', '')
        )


class SafetyCheckUseCase:
    """
    Caso de uso para verificação de segurança veicular e recalls.
    
    Orquestra todo o processo de validação do VIN, consulta à API
    e processamento dos dados de segurança.
    """
    
    def __init__(self, api_adapter: NHTSAAPIAdapter, timeout: int = 30):
        self.api_adapter = api_adapter
        self.timeout = timeout
        self.vin_validator = VINValidator()
        self.recall_processor = RecallDataProcessor()
    
    def execute(self, vin: str) -> SafetyCheckResult:
        """
        Executa a verificação completa de segurança.
        
        Args:
            vin: Número de Identificação do Veículo
            
        Returns:
            SafetyCheckResult: Resultado completo da verificação
            
        Raises:
            InvalidVINError: Se o VIN for inválido
            APIServiceError: Se houver erro na comunicação com a API
            SafetyCheckError: Em caso de outros erros
        """
        start_time = datetime.now()
        logger.info("Iniciando verificação de segurança para VIN: %s", vin)
        
        try:
            # 1. Validação do VIN
            validated_vin = self.vin_validator.validate_vin(vin)
            
            # 2. Extração de informações do VIN
            vin_info = self.vin_validator.extract_vin_info(validated_vin)
            
            # 3. Consulta à API de recalls
            recalls_data = self._fetch_recalls_data(validated_vin)
            
            # 4. Processamento dos recalls
            processed_recalls = self._process_recalls(recalls_data)
            
            # 5. Determinação do status
            status_message = self._generate_status_message(processed_recalls)
            
            # 6. Cálculo do tempo de processamento
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = SafetyCheckResult(
                vin=validated_vin,
                status=status_message,
                recall_count=len(processed_recalls),
                recalls=processed_recalls,
                check_timestamp=datetime.now(),
                vehicle_info=vin_info,
                metadata={
                    'processing_time_seconds': processing_time,
                    'has_critical_recalls': any(
                        recall.severity == RecallSeverity.HIGH 
                        for recall in processed_recalls
                    ),
                    'vin_validation': 'valid',
                    'api_available': True
                }
            )
            
            logger.info(
                "Verificação de segurança concluída: %s - %d recall(s) encontrado(s)",
                validated_vin, len(processed_recalls)
            )
            
            return result
            
        except InvalidVINError:
            logger.warning("Tentativa de verificação com VIN inválido: %s", vin)
            raise
        except Exception as e:
            logger.error("Erro na verificação de segurança para VIN %s: %s", vin, e)
            if isinstance(e, (APIServiceError, SafetyCheckTimeoutError)):
                raise
            else:
                raise APIServiceError(f"Erro na consulta de segurança: {str(e)}")
    
    def _fetch_recalls_data(self, vin: str) -> List[Dict[str, Any]]:
        """
        Busca dados de recalls da API.
        
        Args:
            vin: VIN validado
            
        Returns:
            Lista de dados brutos de recalls
            
        Raises:
            APIServiceError: Se houver erro na API
            SafetyCheckTimeoutError: Se houver timeout
        """
        try:
            logger.debug("Consultando API para VIN: %s", vin)
            recalls_data = self.api_adapter.get_recalls_by_vin(vin)
            
            if not isinstance(recalls_data, list):
                logger.warning("Resposta inesperada da API: %s", type(recalls_data))
                return []
            
            logger.debug("API retornou %d recall(s) para VIN %s", len(recalls_data), vin)
            return recalls_data
            
        except TimeoutError as e:
            logger.error("Timeout na consulta da API para VIN %s: %s", vin, e)
            raise SafetyCheckTimeoutError(f"Timeout na consulta de segurança: {str(e)}")
        except Exception as e:
            logger.error("Erro na API para VIN %s: %s", vin, e)
            raise APIServiceError(f"Erro na API de segurança: {str(e)}")
    
    def _process_recalls(self, recalls_data: List[Dict[str, Any]]) -> List[RecallInfo]:
        """
        Processa dados brutos de recalls.
        
        Args:
            recalls_data: Dados brutos da API
            
        Returns:
            Lista de recalls processados
        """
        processed_recalls = []
        
        for recall_data in recalls_data:
            try:
                processed_recall = self.recall_processor.process_recall_data(recall_data)
                processed_recalls.append(processed_recall)
            except Exception as e:
                logger.warning("Erro ao processar recall: %s", e)
                continue
        
        # Ordena por severidade (alta primeiro)
        severity_order = {RecallSeverity.HIGH: 0, RecallSeverity.MEDIUM: 1, 
                         RecallSeverity.LOW: 2, RecallSeverity.UNKNOWN: 3}
        processed_recalls.sort(key=lambda x: severity_order[x.severity])
        
        return processed_recalls
    
    def _generate_status_message(self, recalls: List[RecallInfo]) -> str:
        """
        Gera mensagem de status baseada nos recalls encontrados.
        
        Args:
            recalls: Lista de recalls processados
            
        Returns:
            Mensagem de status descritiva
        """
        if not recalls:
            return "Nenhum recall de segurança encontrado."
        
        critical_count = sum(1 for r in recalls if r.severity == RecallSeverity.HIGH)
        total_count = len(recalls)
        
        if critical_count > 0:
            return f"⚠️ ALERTA: {critical_count} recall(s) crítico(s) encontrado(s). Total: {total_count} recall(s)."
        else:
            return f"{total_count} recall(s) de segurança encontrado(s)."
    
    def batch_check(self, vins: List[str]) -> List[SafetyCheckResult]:
        """
        Executa verificação em lote para múltiplos VINs.
        
        Args:
            vins: Lista de VINs para verificação
            
        Returns:
            Lista de resultados
        """
        results = []
        
        for vin in vins:
            try:
                result = self.execute(vin)
                results.append(result)
            except SafetyCheckError as e:
                logger.warning("Falha na verificação do VIN %s: %s", vin, e)
                # Cria resultado de erro
                error_result = SafetyCheckResult(
                    vin=vin,
                    status=f"Erro: {str(e)}",
                    recall_count=0,
                    recalls=[],
                    check_timestamp=datetime.now(),
                    vehicle_info=None,
                    metadata={'error': True, 'error_message': str(e)}
                )
                results.append(error_result)
                continue
        
        logger.info(
            "Verificação em lote concluída: %d sucessos, %d erros",
            len([r for r in results if not r.metadata.get('error', False)]),
            len([r for r in results if r.metadata.get('error', False)])
        )
        
        return results


# Exemplo de uso
if __name__ == "__main__":
    # Configuração básica de logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Exemplo de uso (em produção, usar injeção de dependência)
        api_adapter = NHTSAAPIAdapter()
        use_case = SafetyCheckUseCase(api_adapter)
        
        # VIN de exemplo (VIN válido fictício)
        vin = "1HGCM82633A123456"
        
        result = use_case.execute(vin)
        
        print(f"Verificação de segurança concluída!")
        print(f"VIN: {result.vin}")
        print(f"Status: {result.status}")
        print(f"Recalls encontrados: {result.recall_count}")
        print(f"Ano do modelo: {result.vehicle_info.get('model_year', 'N/A')}")
        print(f"Região: {result.vehicle_info.get('manufacturer_region', 'N/A')}")
        
        for i, recall in enumerate(result.recalls, 1):
            print(f"\nRecall {i}:")
            print(f"  Descrição: {recall.description}")
            print(f"  Severidade: {recall.severity.value}")
            print(f"  Componentes: {', '.join(recall.components)}")
            print(f"  Data: {recall.date_reported}")
        
    except SafetyCheckError as e:
        print(f"Erro na verificação de segurança: {e}")