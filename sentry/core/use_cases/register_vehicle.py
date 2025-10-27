# sentry/core/use_cases/register_vehicle.py

import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from sentry.core.entities.vehicle import Vehicle

# Configuração de logging
logger = logging.getLogger(__name__)


# Exceções customizadas
class VehicleRegistrationError(Exception):
    """Exceção base para erros de registro de veículo."""
    pass


class InvalidVehicleDataError(VehicleRegistrationError):
    """Exceção para dados inválidos do veículo."""
    pass


class DuplicatePlateError(VehicleRegistrationError):
    """Exceção quando placa já está cadastrada."""
    pass


class CarrierNotFoundError(VehicleRegistrationError):
    """Exceção quando transportadora não é encontrada."""
    pass


class InvalidYearError(VehicleRegistrationError):
    """Exceção para ano do veículo inválido."""
    pass


class VehicleType(Enum):
    """Tipos de veículos suportados."""
    TRUCK = "caminhao"
    VAN = "van"
    CAR = "carro"
    MOTORCYCLE = "moto"
    PICKUP = "pickup"
    BUS = "onibus"
    TRAILER = "reboque"
    OTHER = "outro"


@dataclass
class VehicleRegistrationResult:
    """Resultado estruturado do registro do veículo."""
    vehicle_id: str
    plate: str
    model: str
    type: str
    carrier_cnpj: Optional[str]
    registration_date: datetime
    status: str
    metadata: Dict[str, Any]


class PlateValidator:
    """Validador para placas de veículos brasileiros."""
    
    # Padrões de placas brasileiras
    PLATE_PATTERNS = {
        'mercosul': re.compile(r'^[A-Z]{3}[0-9][A-Z][0-9]{2}$'),
        'brasil_antigo': re.compile(r'^[A-Z]{3}[0-9]{4}$')
    }
    
    @classmethod
    def validate_plate(cls, plate: str) -> str:
        """
        Valida e formata placa do veículo.
        
        Args:
            plate: Placa a ser validada
            
        Returns:
            Placa formatada
            
        Raises:
            ValueError: Se a placa for inválida
        """
        if not plate or not plate.strip():
            raise ValueError("Placa do veículo é obrigatória")
        
        cleaned_plate = cls._clean_plate(plate)
        
        # Verifica se corresponde a algum padrão
        for plate_type, pattern in cls.PLATE_PATTERNS.items():
            if pattern.match(cleaned_plate):
                logger.debug("Placa válida (%s): %s", plate_type, cleaned_plate)
                return cleaned_plate
        
        raise ValueError(
            f"Placa inválida: {plate}. "
            f"Formatos aceitos: Mercosul (ABC1D23) ou Antigo (ABC1234)"
        )
    
    @staticmethod
    def _clean_plate(plate: str) -> str:
        """
        Limpa e padroniza a placa.
        
        Args:
            plate: Placa bruta
            
        Returns:
            Placa limpa e em maiúsculas
        """
        # Remove caracteres especiais e converte para maiúsculas
        cleaned = re.sub(r'[^A-Z0-9]', '', plate.upper())
        
        # Corrige possíveis confusões de caracteres
        char_replacements = {
            '0': 'O', '1': 'I', '5': 'S', '8': 'B'
        }
        
        # Tenta aplicar substituições se melhorar a validação
        for digit, letter in char_replacements.items():
            temp_plate = cleaned.replace(digit, letter)
            for pattern in PlateValidator.PLATE_PATTERNS.values():
                if pattern.match(temp_plate):
                    return temp_plate
        
        return cleaned
    
    @classmethod
    def format_plate(cls, plate: str) -> str:
        """
        Formata placa para exibição padrão.
        
        Args:
            plate: Placa limpa
            
        Returns:
            Placa formatada
        """
        cleaned = cls._clean_plate(plate)
        
        if len(cleaned) == 7:
            # Formato Mercosul: ABC1D23
            return f"{cleaned[:3]}-{cleaned[3:]}"
        else:
            # Formato antigo: ABC-1234
            return f"{cleaned[:3]}-{cleaned[3:]}"


class ModelValidator:
    """Validador para modelos de veículos."""
    
    MAX_MODEL_LENGTH = 100
    MIN_MODEL_LENGTH = 2
    
    @classmethod
    def validate_model(cls, model: str) -> str:
        """
        Valida modelo do veículo.
        
        Args:
            model: Modelo a ser validado
            
        Returns:
            Modelo validado e limpo
            
        Raises:
            ValueError: Se o modelo for inválido
        """
        if not model or not model.strip():
            raise ValueError("Modelo do veículo é obrigatório")
        
        cleaned_model = model.strip()
        
        if len(cleaned_model) < cls.MIN_MODEL_LENGTH:
            raise ValueError(f"Modelo deve ter pelo menos {cls.MIN_MODEL_LENGTH} caracteres")
        
        if len(cleaned_model) > cls.MAX_MODEL_LENGTH:
            raise ValueError(f"Modelo não pode exceder {cls.MAX_MODEL_LENGTH} caracteres")
        
        # Remove espaços múltiplos
        cleaned_model = re.sub(r'\s+', ' ', cleaned_model)
        
        return cleaned_model


class YearValidator:
    """Validador para anos de veículos."""
    
    @classmethod
    def validate_year(cls, year: Optional[int]) -> Optional[int]:
        """
        Valida ano do veículo.
        
        Args:
            year: Ano a ser validado
            
        Returns:
            Ano validado
            
        Raises:
            InvalidYearError: Se o ano for inválido
        """
        if year is None:
            return None
        
        current_year = datetime.now().year
        min_year = 1900
        
        if year < min_year:
            raise InvalidYearError(f"Ano não pode ser anterior a {min_year}")
        
        if year > current_year + 1:  # Permite veículos do próximo ano
            raise InvalidYearError(f"Ano não pode ser maior que {current_year + 1}")
        
        return year


class ColorValidator:
    """Validador para cores de veículos."""
    
    MAX_COLOR_LENGTH = 50
    
    @classmethod
    def validate_color(cls, color: Optional[str]) -> Optional[str]:
        """
        Valida cor do veículo.
        
        Args:
            color: Cor a ser validada
            
        Returns:
            Cor validada e limpa
        """
        if not color or not color.strip():
            return None
        
        cleaned_color = color.strip()
        
        if len(cleaned_color) > cls.MAX_COLOR_LENGTH:
            raise ValueError(f"Cor não pode exceder {cls.MAX_COLOR_LENGTH} caracteres")
        
        return cleaned_color


class CNPJValidator:
    """Validador de CNPJ para transportadoras."""
    
    @staticmethod
    def clean_cnpj(cnpj: str) -> str:
        """Remove caracteres não numéricos do CNPJ."""
        return ''.join(filter(str.isdigit, cnpj))
    
    @classmethod
    def validate_cnpj(cls, cnpj: Optional[str]) -> Optional[str]:
        """
        Valida CNPJ da transportadora.
        
        Args:
            cnpj: CNPJ a ser validado
            
        Returns:
            CNPJ limpo se válido
            
        Raises:
            ValueError: Se o CNPJ for inválido
        """
        if not cnpj or not cnpj.strip():
            return None
        
        cleaned_cnpj = cls.clean_cnpj(cnpj)
        
        if len(cleaned_cnpj) != 14:
            raise ValueError("CNPJ deve ter 14 dígitos")
        
        # Verificação básica de sequência (pode ser expandida para dígitos verificadores)
        if len(set(cleaned_cnpj)) == 1:
            raise ValueError("CNPJ inválido")
        
        return cleaned_cnpj


class VehicleTypeValidator:
    """Validador para tipos de veículos."""
    
    @classmethod
    def validate_type(cls, vehicle_type: Optional[str]) -> str:
        """
        Valida e normaliza tipo do veículo.
        
        Args:
            vehicle_type: Tipo a ser validado
            
        Returns:
            Tipo normalizado
        """
        if not vehicle_type:
            return VehicleType.OTHER.value
        
        type_lower = vehicle_type.lower().strip()
        
        # Tenta encontrar tipo correspondente
        for vtype in VehicleType:
            if vtype.value == type_lower:
                return vtype.value
        
        # Se não encontrou, usa OTHER
        logger.warning("Tipo de veículo não reconhecido: %s. Usando 'outro'.", vehicle_type)
        return VehicleType.OTHER.value


class ChassisValidator:
    """Validador para número do chassi."""
    
    MIN_CHASSIS_LENGTH = 10
    MAX_CHASSIS_LENGTH = 50
    
    @classmethod
    def validate_chassis(cls, chassis: Optional[str]) -> Optional[str]:
        """
        Valida número do chassi.
        
        Args:
            chassis: Chassi a ser validado
            
        Returns:
            Chassi validado e limpo
        """
        if not chassis or not chassis.strip():
            return None
        
        cleaned_chassis = chassis.strip().upper()
        
        if len(cleaned_chassis) < cls.MIN_CHASSIS_LENGTH:
            raise ValueError(f"Chassi deve ter pelo menos {cls.MIN_CHASSIS_LENGTH} caracteres")
        
        if len(cleaned_chassis) > cls.MAX_CHASSIS_LENGTH:
            raise ValueError(f"Chassi não pode exceder {cls.MAX_CHASSIS_LENGTH} caracteres")
        
        # Remove espaços múltiplos
        cleaned_chassis = re.sub(r'\s+', '', cleaned_chassis)
        
        return cleaned_chassis


class VehicleDataValidator:
    """Validador completo dos dados do veículo."""
    
    @classmethod
    def validate_registration_data(cls, data: Dict) -> List[str]:
        """
        Valida todos os dados de registro do veículo.
        
        Args:
            data: Dados do veículo
            
        Returns:
            Lista de erros de validação (vazia se válido)
        """
        errors = []
        
        # Validação da placa
        try:
            PlateValidator.validate_plate(data.get('plate', ''))
        except ValueError as e:
            errors.append(str(e))
        
        # Validação do modelo
        try:
            ModelValidator.validate_model(data.get('model', ''))
        except ValueError as e:
            errors.append(str(e))
        
        # Validação do ano
        try:
            YearValidator.validate_year(data.get('year'))
        except InvalidYearError as e:
            errors.append(str(e))
        
        # Validação da cor
        try:
            ColorValidator.validate_color(data.get('color'))
        except ValueError as e:
            errors.append(str(e))
        
        # Validação do CNPJ
        try:
            CNPJValidator.validate_cnpj(data.get('carrier_cnpj'))
        except ValueError as e:
            errors.append(str(e))
        
        # Validação do chassi
        try:
            ChassisValidator.validate_chassis(data.get('chassis_number'))
        except ValueError as e:
            errors.append(str(e))
        
        return errors
    
    @classmethod
    def normalize_data(cls, data: Dict) -> Dict:
        """
        Normaliza e formata os dados do veículo.
        
        Args:
            data: Dados brutos
            
        Returns:
            Dados normalizados
        """
        normalized = data.copy()
        
        # Normaliza placa
        if 'plate' in normalized:
            try:
                normalized['plate'] = PlateValidator.validate_plate(normalized['plate'])
            except ValueError:
                raise  # Re-lança pois placa é obrigatória
        
        # Normaliza modelo
        if 'model' in normalized:
            normalized['model'] = ModelValidator.validate_model(normalized['model'])
        
        # Normaliza tipo
        normalized['type'] = VehicleTypeValidator.validate_type(
            normalized.get('type')
        )
        
        # Normaliza CNPJ
        if 'carrier_cnpj' in normalized:
            try:
                normalized['carrier_cnpj'] = CNPJValidator.validate_cnpj(
                    normalized['carrier_cnpj']
                )
            except ValueError:
                normalized['carrier_cnpj'] = None
        
        # Normaliza outros campos opcionais
        optional_fields = {
            'color': ColorValidator.validate_color,
            'year': YearValidator.validate_year,
            'chassis_number': ChassisValidator.validate_chassis
        }
        
        for field, validator in optional_fields.items():
            if field in normalized:
                try:
                    normalized[field] = validator(normalized[field])
                except (ValueError, InvalidYearError):
                    normalized[field] = None
        
        # Garante campos padrão
        if 'color' not in normalized:
            normalized['color'] = None
        
        return normalized


class RegisterVehicleUseCase:
    """
    Caso de uso para registro de veículos.
    
    Responsável por validar, processar e registrar veículos
    no sistema com todas as verificações necessárias.
    """
    
    def __init__(self, vehicle_repository, carrier_repository=None):
        self.vehicle_repository = vehicle_repository
        self.carrier_repository = carrier_repository
        self.validator = VehicleDataValidator()
    
    def execute(self, data: Dict) -> VehicleRegistrationResult:
        """
        Executa o registro do veículo.
        
        Args:
            data: Dados do veículo
            
        Returns:
            VehicleRegistrationResult: Resultado do registro
            
        Raises:
            InvalidVehicleDataError: Se os dados forem inválidos
            DuplicatePlateError: Se a placa já estiver cadastrada
            CarrierNotFoundError: Se a transportadora não for encontrada
            VehicleRegistrationError: Em caso de outros erros
        """
        logger.info("Iniciando registro de veículo: %s", data.get('plate'))
        
        try:
            # 1. Validação dos dados
            validation_errors = self.validator.validate_registration_data(data)
            if validation_errors:
                logger.warning("Dados inválidos para registro: %s", validation_errors)
                raise InvalidVehicleDataError(
                    f"Dados de registro inválidos: {'; '.join(validation_errors)}"
                )
            
            # 2. Normalização dos dados
            normalized_data = self.validator.normalize_data(data)
            plate = normalized_data['plate']
            
            # 3. Verificação de duplicidade
            existing_vehicle = self.vehicle_repository.find_by_plate(plate)
            if existing_vehicle:
                logger.warning("Tentativa de registro com placa duplicada: %s", plate)
                raise DuplicatePlateError(
                    f"Já existe um veículo cadastrado com a placa: {plate}"
                )
            
            # 4. Verificação da transportadora (se fornecida)
            carrier_cnpj = normalized_data.get('carrier_cnpj')
            if carrier_cnpj and self.carrier_repository:
                self._validate_carrier_exists(carrier_cnpj)
            
            # 5. Criação da entidade
            vehicle = self._create_vehicle_entity(normalized_data)
            
            # 6. Persistência
            saved_vehicle = self.vehicle_repository.save(vehicle)
            
            # 7. Log e resultado
            logger.info(
                "Veículo registrado com sucesso: %s %s (Placa: %s)",
                saved_vehicle.model, saved_vehicle.color or '', saved_vehicle.plate
            )
            
            return VehicleRegistrationResult(
                vehicle_id=saved_vehicle.id,
                plate=saved_vehicle.plate,
                model=saved_vehicle.model,
                type=getattr(saved_vehicle, 'type', VehicleType.OTHER.value),
                carrier_cnpj=saved_vehicle.carrier_cnpj,
                registration_date=datetime.now(),
                status="active",
                metadata={
                    'color': saved_vehicle.color,
                    'year': getattr(saved_vehicle, 'year', None),
                    'chassis_number': getattr(saved_vehicle, 'chassis_number', None),
                    'has_carrier': saved_vehicle.carrier_cnpj is not None,
                    'formatted_plate': PlateValidator.format_plate(saved_vehicle.plate)
                }
            )
            
        except (InvalidVehicleDataError, DuplicatePlateError, CarrierNotFoundError):
            raise
        except Exception as e:
            logger.error("Erro inesperado no registro do veículo: %s", e)
            raise VehicleRegistrationError(f"Erro no registro: {str(e)}")
    
    def _validate_carrier_exists(self, cnpj: str) -> None:
        """
        Verifica se a transportadora existe no sistema.
        
        Args:
            cnpj: CNPJ da transportadora
            
        Raises:
            CarrierNotFoundError: Se a transportadora não for encontrada
        """
        try:
            carrier = self.carrier_repository.find_by_cnpj(cnpj)
            if not carrier:
                raise CarrierNotFoundError(f"Transportadora com CNPJ {cnpj} não encontrada")
            
            logger.debug("Transportadora validada: %s", cnpj)
            
        except Exception as e:
            logger.error("Erro ao validar transportadora %s: %s", cnpj, e)
            raise CarrierNotFoundError(f"Erro ao validar transportadora: {str(e)}")
    
    def _create_vehicle_entity(self, data: Dict) -> Vehicle:
        """
        Cria entidade Vehicle a partir dos dados validados.
        
        Args:
            data: Dados validados e normalizados
            
        Returns:
            Instância de Vehicle
        """
        # Campos obrigatórios
        vehicle_data = {
            'plate': data['plate'],
            'model': data['model']
        }
        
        # Campos opcionais
        optional_fields = [
            'color', 'carrier_cnpj', 'type', 'year', 'chassis_number',
            'fuel_type', 'capacity_kg', 'capacity_m3', 'insurance_policy',
            'last_maintenance', 'next_maintenance', 'status', 'notes'
        ]
        
        for field in optional_fields:
            if field in data and data[field] is not None:
                vehicle_data[field] = data[field]
        
        return Vehicle(**vehicle_data)
    
    def batch_register(self, vehicles_data: List[Dict]) -> List[VehicleRegistrationResult]:
        """
        Registra múltiplos veículos em lote.
        
        Args:
            vehicles_data: Lista de dados dos veículos
            
        Returns:
            Lista de resultados
        """
        results = []
        
        for data in vehicles_data:
            try:
                result = self.execute(data)
                results.append(result)
            except VehicleRegistrationError as e:
                logger.warning(
                    "Falha no registro do veículo %s: %s",
                    data.get('plate'), e
                )
                # Continua com os próximos veículos
                continue
        
        logger.info(
            "Registro em lote concluído: %d sucessos, %d falhas",
            len(results), len(vehicles_data) - len(results)
        )
        
        return results


# Exemplo de uso
if __name__ == "__main__":
    # Configuração básica de logging
    logging.basicConfig(level=logging.INFO)
    
    # Exemplo de uso (em produção, usar injeção de dependência)
    class MockVehicleRepository:
        def __init__(self):
            self.vehicles = []
        
        def find_by_plate(self, plate):
            return next((v for v in self.vehicles if v.plate == plate), None)
        
        def save(self, vehicle):
            vehicle.id = f"VEH{len(self.vehicles) + 1:04d}"
            self.vehicles.append(vehicle)
            return vehicle
    
    class MockCarrierRepository:
        def find_by_cnpj(self, cnpj):
            # Simula verificação de transportadora
            return cnpj in ["12345678000195", "98765432000187"]
    
    try:
        repository = MockVehicleRepository()
        carrier_repo = MockCarrierRepository()
        use_case = RegisterVehicleUseCase(repository, carrier_repo)
        
        # Dados de exemplo
        vehicle_data = {
            'plate': 'ABC1D23',
            'model': 'Volvo FH 540',
            'color': 'Azul',
            'type': 'caminhao',
            'year': 2023,
            'carrier_cnpj': '12345678000195',
            'chassis_number': '9BR12345678901234',
            'fuel_type': 'diesel',
            'capacity_kg': 25000,
            'capacity_m3': 80
        }
        
        result = use_case.execute(vehicle_data)
        print(f"Veículo registrado com sucesso!")
        print(f"ID: {result.vehicle_id}")
        print(f"Placa: {result.plate} ({result.metadata['formatted_plate']})")
        print(f"Modelo: {result.model}")
        print(f"Tipo: {result.type}")
        print(f"Transportadora: {result.carrier_cnpj}")
        print(f"Cor: {result.metadata['color']}")
        print(f"Ano: {result.metadata['year']}")
        
    except VehicleRegistrationError as e:
        print(f"Erro no registro: {e}")