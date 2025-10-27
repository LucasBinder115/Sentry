# sentry/core/use_cases/register_merchandise.py

import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass
from enum import Enum

from sentry.core.entities.merchandise import Merchandise

# Configuração de logging
logger = logging.getLogger(__name__)


# Exceções customizadas
class MerchandiseRegistrationError(Exception):
    """Exceção base para erros de registro de mercadoria."""
    pass


class InvalidMerchandiseDataError(MerchandiseRegistrationError):
    """Exceção para dados inválidos da mercadoria."""
    pass


class VehicleNotFoundError(MerchandiseRegistrationError):
    """Exceção quando veículo não é encontrado."""
    pass


class InvalidWeightError(MerchandiseRegistrationError):
    """Exceção para peso inválido."""
    pass


class InvalidVolumeError(MerchandiseRegistrationError):
    """Exceção para volume inválido."""
    pass


class MerchandiseCategory(Enum):
    """Categorias de mercadorias."""
    ELETRONICOS = "eletronicos"
    ELETRODOMESTICOS = "eletrodomesticos"
    MOVES = "moveis"
    ROUPAS = "roupas"
    ALIMENTOS = "alimentos"
    BEBIDAS = "bebidas"
    MATERIAL_CONSTRUCAO = "material_construcao"
    QUIMICOS = "quimicos"
    OUTROS = "outros"


@dataclass
class MerchandiseRegistrationResult:
    """Resultado estruturado do registro da mercadoria."""
    merchandise_id: str
    description: str
    category: str
    weight: Optional[Decimal]
    volume: Optional[Decimal]
    vehicle_plate: Optional[str]
    registration_date: datetime
    status: str
    metadata: Dict[str, Any]


class WeightValidator:
    """Validador para pesos de mercadorias."""
    
    MAX_WEIGHT_KG = Decimal('50000')  # 50 toneladas
    MIN_WEIGHT_KG = Decimal('0.001')  # 1 grama
    
    @classmethod
    def validate_weight(cls, weight: Any) -> Optional[Decimal]:
        """
        Valida e converte peso para Decimal.
        
        Args:
            weight: Peso a ser validado
            
        Returns:
            Peso como Decimal se válido, None se vazio
            
        Raises:
            InvalidWeightError: Se o peso for inválido
        """
        if weight is None or weight == "":
            return None
        
        try:
            if isinstance(weight, (int, float)):
                weight_decimal = Decimal(str(weight))
            else:
                weight_decimal = Decimal(str(weight).replace(',', '.'))
            
            if weight_decimal < cls.MIN_WEIGHT_KG:
                raise InvalidWeightError(f"Peso não pode ser menor que {cls.MIN_WEIGHT_KG} kg")
            
            if weight_decimal > cls.MAX_WEIGHT_KG:
                raise InvalidWeightError(f"Peso não pode exceder {cls.MAX_WEIGHT_KG} kg")
            
            return weight_decimal.quantize(Decimal('0.001'))  # Precisão de 1 grama
            
        except (InvalidOperation, ValueError):
            raise InvalidWeightError("Formato de peso inválido. Use números com até 3 casas decimais.")


class VolumeValidator:
    """Validador para volumes de mercadorias."""
    
    MAX_VOLUME_M3 = Decimal('100')  # 100 m³
    MIN_VOLUME_M3 = Decimal('0.001')  # 0.001 m³
    
    @classmethod
    def validate_volume(cls, volume: Any) -> Optional[Decimal]:
        """
        Valida e converte volume para Decimal.
        
        Args:
            volume: Volume a ser validado
            
        Returns:
            Volume como Decimal se válido, None se vazio
            
        Raises:
            InvalidVolumeError: Se o volume for inválido
        """
        if volume is None or volume == "":
            return None
        
        try:
            if isinstance(volume, (int, float)):
                volume_decimal = Decimal(str(volume))
            else:
                volume_decimal = Decimal(str(volume).replace(',', '.'))
            
            if volume_decimal < cls.MIN_VOLUME_M3:
                raise InvalidVolumeError(f"Volume não pode ser menor que {cls.MIN_VOLUME_M3} m³")
            
            if volume_decimal > cls.MAX_VOLUME_M3:
                raise InvalidVolumeError(f"Volume não pode exceder {cls.MAX_VOLUME_M3} m³")
            
            return volume_decimal.quantize(Decimal('0.001'))  # Precisão de 0.001 m³
            
        except (InvalidOperation, ValueError):
            raise InvalidVolumeError("Formato de volume inválido. Use números com até 3 casas decimais.")


class PlateValidator:
    """Validador para placas de veículos."""
    
    # Padrões de placas brasileiras
    PLATE_PATTERNS = {
        'mercosul': re.compile(r'^[A-Z]{3}[0-9][A-Z][0-9]{2}$'),
        'brasil_antigo': re.compile(r'^[A-Z]{3}[0-9]{4}$')
    }
    
    @classmethod
    def validate_plate(cls, plate: Optional[str]) -> Optional[str]:
        """
        Valida formato da placa do veículo.
        
        Args:
            plate: Placa a ser validada
            
        Returns:
            Placa formatada se válida, None se vazia
            
        Raises:
            ValueError: Se a placa for inválida
        """
        if not plate or plate.strip() == "":
            return None
        
        cleaned_plate = cls._clean_plate(plate)
        
        # Verifica se corresponde a algum padrão
        for pattern in cls.PLATE_PATTERNS.values():
            if pattern.match(cleaned_plate):
                return cleaned_plate
        
        raise ValueError(f"Placa inválida: {plate}. Formatos aceitos: Mercosul (ABC1D23) ou Antigo (ABC1234)")
    
    @staticmethod
    def _clean_plate(plate: str) -> str:
        """
        Limpa e padroniza a placa.
        
        Args:
            plate: Placa bruta
            
        Returns:
            Placa limpa
        """
        return re.sub(r'[^A-Z0-9]', '', plate.upper())


class CategoryValidator:
    """Validador para categorias de mercadorias."""
    
    @classmethod
    def validate_category(cls, category: Optional[str]) -> str:
        """
        Valida e normaliza categoria da mercadoria.
        
        Args:
            category: Categoria a ser validada
            
        Returns:
            Categoria normalizada
            
        Raises:
            ValueError: Se a categoria for inválida
        """
        if not category:
            return MerchandiseCategory.OUTROS.value
        
        category_lower = category.lower().strip()
        
        # Tenta encontrar categoria correspondente
        for cat in MerchandiseCategory:
            if cat.value == category_lower:
                return cat.value
        
        # Se não encontrou, usa OUTROS
        logger.warning("Categoria não reconhecida: %s. Usando 'outros'.", category)
        return MerchandiseCategory.OUTROS.value


class DescriptionValidator:
    """Validador para descrições de mercadorias."""
    
    MAX_DESCRIPTION_LENGTH = 500
    MIN_DESCRIPTION_LENGTH = 3
    
    @classmethod
    def validate_description(cls, description: str) -> str:
        """
        Valida e limpa descrição da mercadoria.
        
        Args:
            description: Descrição a ser validada
            
        Returns:
            Descrição validada e limpa
            
        Raises:
            ValueError: Se a descrição for inválida
        """
        if not description or not description.strip():
            raise ValueError("Descrição da mercadoria é obrigatória")
        
        cleaned_description = description.strip()
        
        if len(cleaned_description) < cls.MIN_DESCRIPTION_LENGTH:
            raise ValueError(f"Descrição deve ter pelo menos {cls.MIN_DESCRIPTION_LENGTH} caracteres")
        
        if len(cleaned_description) > cls.MAX_DESCRIPTION_LENGTH:
            raise ValueError(f"Descrição não pode exceder {cls.MAX_DESCRIPTION_LENGTH} caracteres")
        
        # Remove espaços múltiplos
        cleaned_description = re.sub(r'\s+', ' ', cleaned_description)
        
        return cleaned_description


class NotesValidator:
    """Validador para observações."""
    
    MAX_NOTES_LENGTH = 1000
    
    @classmethod
    def validate_notes(cls, notes: Optional[str]) -> Optional[str]:
        """
        Valida observações da mercadoria.
        
        Args:
            notes: Observações a serem validadas
            
        Returns:
            Observações validadas e limpas
        """
        if not notes or not notes.strip():
            return None
        
        cleaned_notes = notes.strip()
        
        if len(cleaned_notes) > cls.MAX_NOTES_LENGTH:
            raise ValueError(f"Observações não podem exceder {cls.MAX_NOTES_LENGTH} caracteres")
        
        return cleaned_notes


class MerchandiseDataValidator:
    """Validador completo dos dados da mercadoria."""
    
    @classmethod
    def validate_registration_data(cls, data: Dict) -> Dict[str, List[str]]:
        """
        Valida todos os dados de registro da mercadoria.
        
        Args:
            data: Dados da mercadoria
            
        Returns:
            Dicionário com 'errors' e 'warnings'
        """
        errors = []
        warnings = []
        
        # Validação da descrição
        try:
            DescriptionValidator.validate_description(data.get('description', ''))
        except ValueError as e:
            errors.append(str(e))
        
        # Validação do peso
        try:
            WeightValidator.validate_weight(data.get('weight'))
        except InvalidWeightError as e:
            errors.append(str(e))
        
        # Validação do volume
        try:
            VolumeValidator.validate_volume(data.get('volume'))
        except InvalidVolumeError as e:
            errors.append(str(e))
        
        # Validação da placa
        try:
            PlateValidator.validate_plate(data.get('vehicle_plate'))
        except ValueError as e:
            errors.append(str(e))
        
        # Validação da categoria
        try:
            CategoryValidator.validate_category(data.get('category'))
        except ValueError as e:
            warnings.append(str(e))
        
        # Validação das observações
        try:
            NotesValidator.validate_notes(data.get('notes'))
        except ValueError as e:
            warnings.append(str(e))
        
        # Verificação de dados mínimos
        if not data.get('weight') and not data.get('volume'):
            warnings.append("Nenhum peso ou volume informado. Considere adicionar estas informações.")
        
        return {'errors': errors, 'warnings': warnings}
    
    @classmethod
    def normalize_data(cls, data: Dict) -> Dict:
        """
        Normaliza e formata os dados da mercadoria.
        
        Args:
            data: Dados brutos
            
        Returns:
            Dados normalizados
        """
        normalized = data.copy()
        
        # Normaliza descrição
        if 'description' in normalized:
            normalized['description'] = normalized['description'].strip()
        
        # Normaliza peso
        if 'weight' in normalized:
            try:
                normalized['weight'] = WeightValidator.validate_weight(normalized['weight'])
            except InvalidWeightError:
                normalized['weight'] = None
        
        # Normaliza volume
        if 'volume' in normalized:
            try:
                normalized['volume'] = VolumeValidator.validate_volume(normalized['volume'])
            except InvalidVolumeError:
                normalized['volume'] = None
        
        # Normaliza placa
        if 'vehicle_plate' in normalized:
            try:
                normalized['vehicle_plate'] = PlateValidator.validate_plate(normalized['vehicle_plate'])
            except ValueError:
                normalized['vehicle_plate'] = None
        
        # Normaliza categoria
        if 'category' in normalized:
            normalized['category'] = CategoryValidator.validate_category(normalized['category'])
        else:
            normalized['category'] = MerchandiseCategory.OUTROS.value
        
        # Normaliza observações
        if 'notes' in normalized:
            try:
                normalized['notes'] = NotesValidator.validate_notes(normalized['notes'])
            except ValueError:
                normalized['notes'] = None
        
        return normalized


class RegisterMerchandiseUseCase:
    """
    Caso de uso para registro de mercadorias.
    
    Responsável por validar, processar e registrar mercadorias
    no sistema com todas as verificações necessárias.
    """
    
    def __init__(self, merchandise_repository, vehicle_repository=None):
        self.merchandise_repository = merchandise_repository
        self.vehicle_repository = vehicle_repository
        self.validator = MerchandiseDataValidator()
    
    def execute(self, data: Dict) -> MerchandiseRegistrationResult:
        """
        Executa o registro da mercadoria.
        
        Args:
            data: Dados da mercadoria
            
        Returns:
            MerchandiseRegistrationResult: Resultado do registro
            
        Raises:
            InvalidMerchandiseDataError: Se os dados forem inválidos
            VehicleNotFoundError: Se o veículo não for encontrado
            MerchandiseRegistrationError: Em caso de outros erros
        """
        logger.info("Iniciando registro de mercadoria: %s", data.get('description', '')[:50])
        
        try:
            # 1. Validação dos dados
            validation_result = self.validator.validate_registration_data(data)
            
            if validation_result['errors']:
                logger.warning("Dados inválidos para registro: %s", validation_result['errors'])
                raise InvalidMerchandiseDataError(
                    f"Dados de registro inválidos: {'; '.join(validation_result['errors'])}"
                )
            
            # Log de warnings
            if validation_result['warnings']:
                logger.info("Warnings no registro: %s", validation_result['warnings'])
            
            # 2. Normalização dos dados
            normalized_data = self.validator.normalize_data(data)
            
            # 3. Verificação do veículo (se fornecido e se repositório disponível)
            vehicle_plate = normalized_data.get('vehicle_plate')
            if vehicle_plate and self.vehicle_repository:
                self._validate_vehicle_exists(vehicle_plate)
            
            # 4. Criação da entidade
            merchandise = self._create_merchandise_entity(normalized_data)
            
            # 5. Persistência
            saved_merchandise = self.merchandise_repository.save(merchandise)
            
            # 6. Log e resultado
            logger.info(
                "Mercadoria registrada com sucesso: %s (ID: %s)",
                saved_merchandise.description, saved_merchandise.id
            )
            
            return MerchandiseRegistrationResult(
                merchandise_id=saved_merchandise.id,
                description=saved_merchandise.description,
                category=getattr(saved_merchandise, 'category', MerchandiseCategory.OUTROS.value),
                weight=saved_merchandise.weight,
                volume=saved_merchandise.volume,
                vehicle_plate=saved_merchandise.vehicle_plate,
                registration_date=datetime.now(),
                status="registered",
                metadata={
                    'has_notes': bool(saved_merchandise.notes),
                    'has_weight': saved_merchandise.weight is not None,
                    'has_volume': saved_merchandise.volume is not None,
                    'has_vehicle': saved_merchandise.vehicle_plate is not None,
                    'warnings': validation_result['warnings']
                }
            )
            
        except (InvalidMerchandiseDataError, VehicleNotFoundError):
            raise
        except Exception as e:
            logger.error("Erro inesperado no registro da mercadoria: %s", e)
            raise MerchandiseRegistrationError(f"Erro no registro: {str(e)}")
    
    def _validate_vehicle_exists(self, plate: str) -> None:
        """
        Verifica se o veículo existe no sistema.
        
        Args:
            plate: Placa do veículo
            
        Raises:
            VehicleNotFoundError: Se o veículo não for encontrado
        """
        try:
            vehicle = self.vehicle_repository.find_by_plate(plate)
            if not vehicle:
                raise VehicleNotFoundError(f"Veículo com placa {plate} não encontrado")
            
            logger.debug("Veículo validado: %s", plate)
            
        except Exception as e:
            logger.error("Erro ao validar veículo %s: %s", plate, e)
            raise VehicleNotFoundError(f"Erro ao validar veículo: {str(e)}")
    
    def _create_merchandise_entity(self, data: Dict) -> Merchandise:
        """
        Cria entidade Merchandise a partir dos dados validados.
        
        Args:
            data: Dados validados e normalizados
            
        Returns:
            Instância de Merchandise
        """
        # Campos base
        merchandise_data = {
            'description': data['description']
        }
        
        # Campos opcionais
        optional_fields = [
            'weight', 'volume', 'vehicle_plate', 'notes', 'category',
            'value', 'insurance_required', 'fragile', 'hazardous',
            'special_handling', 'storage_temperature'
        ]
        
        for field in optional_fields:
            if field in data and data[field] is not None:
                merchandise_data[field] = data[field]
        
        return Merchandise(**merchandise_data)
    
    def batch_register(self, merchandise_list: List[Dict]) -> List[MerchandiseRegistrationResult]:
        """
        Registra múltiplas mercadorias em lote.
        
        Args:
            merchandise_list: Lista de dados das mercadorias
            
        Returns:
            Lista de resultados
        """
        results = []
        
        for data in merchandise_list:
            try:
                result = self.execute(data)
                results.append(result)
            except MerchandiseRegistrationError as e:
                logger.warning(
                    "Falha no registro da mercadoria %s: %s",
                    data.get('description', 'Desconhecida'), e
                )
                # Continua com as próximas mercadorias
                continue
        
        logger.info(
            "Registro em lote concluído: %d sucessos, %d falhas",
            len(results), len(merchandise_list) - len(results)
        )
        
        return results


# Exemplo de uso
if __name__ == "__main__":
    # Configuração básica de logging
    logging.basicConfig(level=logging.INFO)
    
    # Exemplo de uso (em produção, usar injeção de dependência)
    class MockMerchandiseRepository:
        def __init__(self):
            self.merchandises = []
        
        def save(self, merchandise):
            merchandise.id = f"MERCH{len(self.merchandises) + 1:04d}"
            self.merchandises.append(merchandise)
            return merchandise
    
    class MockVehicleRepository:
        def find_by_plate(self, plate):
            # Simula verificação de veículo
            return plate in ["ABC1D23", "XYZ9W87"]
    
    try:
        repository = MockMerchandiseRepository()
        vehicle_repo = MockVehicleRepository()
        use_case = RegisterMerchandiseUseCase(repository, vehicle_repo)
        
        # Dados de exemplo
        merchandise_data = {
            'description': 'Notebook Dell Inspiron 15 5000',
            'weight': 2.5,
            'volume': 0.015,
            'vehicle_plate': 'ABC1D23',
            'category': 'eletronicos',
            'value': 3500.00,
            'fragile': True,
            'insurance_required': True,
            'notes': 'Manuseio com cuidado. Produto frágil.'
        }
        
        result = use_case.execute(merchandise_data)
        print(f"Mercadoria registrada com sucesso!")
        print(f"ID: {result.merchandise_id}")
        print(f"Descrição: {result.description}")
        print(f"Categoria: {result.category}")
        print(f"Peso: {result.weight} kg")
        print(f"Volume: {result.volume} m³")
        print(f"Veículo: {result.vehicle_plate}")
        
    except MerchandiseRegistrationError as e:
        print(f"Erro no registro: {e}")