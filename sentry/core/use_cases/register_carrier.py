# sentry/core/use_cases/register_carrier.py

import logging
import re
from typing import Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass
from decimal import Decimal

from sentry.core.entities.carrier import Carrier

# Configuração de logging
logger = logging.getLogger(__name__)


# Exceções customizadas
class CarrierRegistrationError(Exception):
    """Exceção base para erros de registro de transportadora."""
    pass


class InvalidCarrierDataError(CarrierRegistrationError):
    """Exceção para dados inválidos da transportadora."""
    pass


class DuplicateCNPJError(CarrierRegistrationError):
    """Exceção quando CNPJ já está cadastrado."""
    pass


class CarrierValidationError(CarrierRegistrationError):
    """Exceção para erros de validação específicos."""
    pass


@dataclass
class CarrierRegistrationResult:
    """Resultado estruturado do registro da transportadora."""
    carrier_id: str
    name: str
    cnpj: str
    registration_date: datetime
    status: str
    metadata: Dict[str, any]


class CNPJValidator:
    """Validador de CNPJ com verificação de dígitos."""
    
    @staticmethod
    def clean_cnpj(cnpj: str) -> str:
        """
        Remove caracteres não numéricos do CNPJ.
        
        Args:
            cnpj: CNPJ a ser limpo
            
        Returns:
            CNPJ contendo apenas dígitos
        """
        return ''.join(filter(str.isdigit, cnpj))
    
    @staticmethod
    def is_sequential(cnpj: str) -> bool:
        """
        Verifica se o CNPJ é uma sequência de números iguais.
        
        Args:
            cnpj: CNPJ a ser verificado
            
        Returns:
            True se for sequência, False caso contrário
        """
        return len(set(cnpj)) == 1
    
    @staticmethod
    def calculate_verification_digit(cnpj_partial: str, weight_start: int) -> int:
        """
        Calcula dígito verificador do CNPJ.
        
        Args:
            cnpj_partial: Parte do CNPJ para cálculo
            weight_start: Peso inicial para multiplicação
            
        Returns:
            Dígito verificador calculado
        """
        if weight_start == 5:
            weights = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        else:  # weight_start == 6
            weights = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        
        total = sum(int(digit) * weight for digit, weight in zip(cnpj_partial, weights))
        remainder = total % 11
        return 0 if remainder < 2 else 11 - remainder
    
    @classmethod
    def validate_cnpj(cls, cnpj: str) -> bool:
        """
        Valida o CNPJ de forma completa.
        
        Args:
            cnpj: CNPJ a ser validado
            
        Returns:
            True se CNPJ é válido
        """
        try:
            cleaned_cnpj = cls.clean_cnpj(cnpj)
            
            # Verifica tamanho
            if len(cleaned_cnpj) != 14:
                return False
            
            # Verifica sequência
            if cls.is_sequential(cleaned_cnpj):
                return False
            
            # Calcula primeiro dígito verificador
            first_digit = cls.calculate_verification_digit(cleaned_cnpj[:12], 5)
            if first_digit != int(cleaned_cnpj[12]):
                return False
            
            # Calcula segundo dígito verificador
            second_digit = cls.calculate_verification_digit(cleaned_cnpj[:13], 6)
            return second_digit == int(cleaned_cnpj[13])
            
        except Exception:
            return False


class PhoneValidator:
    """Validador de números de telefone."""
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """
        Valida formato de telefone brasileiro.
        
        Args:
            phone: Número de telefone
            
        Returns:
            True se telefone é válido
        """
        if not phone:
            return True  # Telefone é opcional
        
        # Remove caracteres não numéricos
        cleaned_phone = ''.join(filter(str.isdigit, phone))
        
        # Verifica se tem entre 10 e 11 dígitos (com DDD)
        if len(cleaned_phone) not in [10, 11]:
            return False
        
        # Verifica se o DDD é válido (11 a 99)
        ddd = int(cleaned_phone[:2])
        if not (11 <= ddd <= 99):
            return False
        
        return True
    
    @staticmethod
    def format_phone(phone: str) -> str:
        """
        Formata telefone para padrão brasileiro.
        
        Args:
            phone: Número de telefone
            
        Returns:
            Telefone formatado
        """
        if not phone:
            return ""
        
        cleaned_phone = ''.join(filter(str.isdigit, phone))
        
        if len(cleaned_phone) == 10:
            return f"({cleaned_phone[:2]}) {cleaned_phone[2:6]}-{cleaned_phone[6:]}"
        elif len(cleaned_phone) == 11:
            return f"({cleaned_phone[:2]}) {cleaned_phone[2:7]}-{cleaned_phone[7:]}"
        else:
            return phone


class EmailValidator:
    """Validador de endereços de email."""
    
    EMAIL_REGEX = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    @classmethod
    def validate_email(cls, email: str) -> bool:
        """
        Valida formato de email.
        
        Args:
            email: Email a ser validado
            
        Returns:
            True se email é válido
        """
        if not email:
            return True  # Email é opcional
            
        return bool(cls.EMAIL_REGEX.match(email.strip()))


class CarrierDataValidator:
    """Validador completo dos dados da transportadora."""
    
    @classmethod
    def validate_registration_data(cls, data: Dict) -> List[str]:
        """
        Valida todos os dados de registro da transportadora.
        
        Args:
            data: Dados da transportadora
            
        Returns:
            Lista de erros de validação (vazia se válido)
        """
        errors = []
        
        # Validação do nome
        name = data.get('name', '').strip()
        if not name:
            errors.append("Nome da transportadora é obrigatório.")
        elif len(name) < 3:
            errors.append("Nome da transportadora deve ter pelo menos 3 caracteres.")
        elif len(name) > 255:
            errors.append("Nome da transportadora não pode exceder 255 caracteres.")
        
        # Validação do CNPJ
        cnpj = data.get('cnpj', '')
        if not cnpj:
            errors.append("CNPJ é obrigatório.")
        elif not CNPJValidator.validate_cnpj(cnpj):
            errors.append("CNPJ inválido.")
        
        # Validação do nome do responsável
        responsible_name = data.get('responsible_name', '').strip()
        if responsible_name and len(responsible_name) > 100:
            errors.append("Nome do responsável não pode exceder 100 caracteres.")
        
        # Validação do telefone
        contact_phone = data.get('contact_phone', '')
        if contact_phone and not PhoneValidator.validate_phone(contact_phone):
            errors.append("Telefone de contato inválido.")
        
        # Validação do email
        email = data.get('email', '')
        if email and not EmailValidator.validate_email(email):
            errors.append("Email inválido.")
        
        # Validação do endereço (se fornecido)
        address = data.get('address', {})
        if address:
            address_errors = cls._validate_address(address)
            errors.extend(address_errors)
        
        return errors
    
    @classmethod
    def _validate_address(cls, address: Dict) -> List[str]:
        """Valida dados de endereço."""
        errors = []
        
        street = address.get('street', '').strip()
        if street and len(street) > 200:
            errors.append("Logradouro não pode exceder 200 caracteres.")
        
        city = address.get('city', '').strip()
        if city and len(city) > 100:
            errors.append("Cidade não pode exceder 100 caracteres.")
        
        state = address.get('state', '').strip()
        if state and len(state) != 2:
            errors.append("Estado deve ter 2 caracteres (UF).")
        
        zip_code = address.get('zip_code', '').strip()
        if zip_code:
            cleaned_zip = ''.join(filter(str.isdigit, zip_code))
            if len(cleaned_zip) != 8:
                errors.append("CEP deve ter 8 dígitos.")
        
        return errors
    
    @classmethod
    def normalize_data(cls, data: Dict) -> Dict:
        """
        Normaliza e formata os dados da transportadora.
        
        Args:
            data: Dados brutos
            
        Returns:
            Dados normalizados
        """
        normalized = data.copy()
        
        # Normaliza CNPJ
        if 'cnpj' in normalized:
            normalized['cnpj'] = CNPJValidator.clean_cnpj(normalized['cnpj'])
        
        # Normaliza telefone
        if 'contact_phone' in normalized:
            normalized['contact_phone'] = PhoneValidator.format_phone(
                normalized['contact_phone']
            )
        
        # Normaliza strings (remove espaços extras)
        string_fields = ['name', 'responsible_name', 'email']
        for field in string_fields:
            if field in normalized and normalized[field]:
                normalized[field] = normalized[field].strip()
        
        # Normaliza endereço
        if 'address' in normalized and normalized['address']:
            address = normalized['address'].copy()
            address_fields = ['street', 'number', 'complement', 'neighborhood', 'city']
            for field in address_fields:
                if field in address and address[field]:
                    address[field] = address[field].strip()
            
            if 'state' in address and address['state']:
                address['state'] = address['state'].upper().strip()
            
            if 'zip_code' in address and address['zip_code']:
                address['zip_code'] = ''.join(filter(str.isdigit, address['zip_code']))
            
            normalized['address'] = address
        
        return normalized


class RegisterCarrierUseCase:
    """
    Caso de uso para registro de transportadoras.
    
    Responsável por validar, processar e registrar transportadoras
    no sistema com todas as verificações necessárias.
    """
    
    def __init__(self, carrier_repository):
        self.carrier_repository = carrier_repository
        self.validator = CarrierDataValidator()
    
    def execute(self, data: Dict) -> CarrierRegistrationResult:
        """
        Executa o registro da transportadora.
        
        Args:
            data: Dados da transportadora
            
        Returns:
            CarrierRegistrationResult: Resultado do registro
            
        Raises:
            InvalidCarrierDataError: Se os dados forem inválidos
            DuplicateCNPJError: Se o CNPJ já estiver cadastrado
            CarrierRegistrationError: Em caso de outros erros
        """
        logger.info("Iniciando registro de transportadora: %s", data.get('name'))
        
        try:
            # 1. Validação dos dados
            validation_errors = self.validator.validate_registration_data(data)
            if validation_errors:
                logger.warning("Dados inválidos para registro: %s", validation_errors)
                raise InvalidCarrierDataError(
                    f"Dados de registro inválidos: {'; '.join(validation_errors)}"
                )
            
            # 2. Normalização dos dados
            normalized_data = self.validator.normalize_data(data)
            cnpj = normalized_data['cnpj']
            
            # 3. Verificação de duplicidade
            existing_carrier = self.carrier_repository.find_by_cnpj(cnpj)
            if existing_carrier:
                logger.warning("Tentativa de registro com CNPJ duplicado: %s", cnpj)
                raise DuplicateCNPJError(
                    f"Já existe uma transportadora cadastrada com o CNPJ: {cnpj}"
                )
            
            # 4. Criação da entidade
            carrier = self._create_carrier_entity(normalized_data)
            
            # 5. Persistência
            saved_carrier = self.carrier_repository.save(carrier)
            
            # 6. Log e resultado
            logger.info(
                "Transportadora registrada com sucesso: %s (ID: %s, CNPJ: %s)",
                saved_carrier.name, saved_carrier.id, saved_carrier.cnpj
            )
            
            return CarrierRegistrationResult(
                carrier_id=saved_carrier.id,
                name=saved_carrier.name,
                cnpj=saved_carrier.cnpj,
                registration_date=datetime.now(),
                status="active",
                metadata={
                    'responsible_name': saved_carrier.responsible_name,
                    'contact_phone': saved_carrier.contact_phone,
                    'has_address': hasattr(saved_carrier, 'address') and bool(saved_carrier.address)
                }
            )
            
        except (InvalidCarrierDataError, DuplicateCNPJError):
            raise
        except Exception as e:
            logger.error("Erro inesperado no registro da transportadora: %s", e)
            raise CarrierRegistrationError(f"Erro no registro: {str(e)}")
    
    def _create_carrier_entity(self, data: Dict) -> Carrier:
        """
        Cria entidade Carrier a partir dos dados validados.
        
        Args:
            data: Dados validados e normalizados
            
        Returns:
            Instância de Carrier
        """
        # Campos obrigatórios
        carrier_data = {
            'name': data['name'],
            'cnpj': data['cnpj']
        }
        
        # Campos opcionais
        optional_fields = [
            'responsible_name', 'contact_phone', 'email', 
            'address', 'operating_regions', 'vehicle_types',
            'capacity_kg', 'insurance_value', 'notes'
        ]
        
        for field in optional_fields:
            if field in data and data[field] is not None:
                carrier_data[field] = data[field]
        
        return Carrier(**carrier_data)
    
    def batch_register(self, carriers_data: List[Dict]) -> List[CarrierRegistrationResult]:
        """
        Registra múltiplas transportadoras em lote.
        
        Args:
            carriers_data: Lista de dados das transportadoras
            
        Returns:
            Lista de resultados
        """
        results = []
        
        for data in carriers_data:
            try:
                result = self.execute(data)
                results.append(result)
            except CarrierRegistrationError as e:
                logger.warning(
                    "Falha no registro da transportadora %s: %s",
                    data.get('name'), e
                )
                # Continua com as próximas transportadoras
                continue
        
        logger.info(
            "Registro em lote concluído: %d sucessos, %d falhas",
            len(results), len(carriers_data) - len(results)
        )
        
        return results


# Exemplo de uso
if __name__ == "__main__":
    # Configuração básica de logging
    logging.basicConfig(level=logging.INFO)
    
    # Exemplo de uso (em produção, usar injeção de dependência)
    class MockCarrierRepository:
        def __init__(self):
            self.carriers = []
        
        def find_by_cnpj(self, cnpj):
            return next((c for c in self.carriers if c.cnpj == cnpj), None)
        
        def save(self, carrier):
            carrier.id = f"CAR{len(self.carriers) + 1:04d}"
            self.carriers.append(carrier)
            return carrier
    
    try:
        repository = MockCarrierRepository()
        use_case = RegisterCarrierUseCase(repository)
        
        # Dados de exemplo
        carrier_data = {
            'name': 'Transportadora Expresso Brasil LTDA',
            'cnpj': '12.345.678/0001-95',  # CNPJ válido para exemplo
            'responsible_name': 'João Silva',
            'contact_phone': '(11) 99999-9999',
            'email': 'contato@expressobrasil.com.br',
            'address': {
                'street': 'Rua das Flores',
                'number': '123',
                'complement': 'Sala 45',
                'neighborhood': 'Centro',
                'city': 'São Paulo',
                'state': 'SP',
                'zip_code': '01234-567'
            }
        }
        
        result = use_case.execute(carrier_data)
        print(f"Transportadora registrada com sucesso!")
        print(f"ID: {result.carrier_id}")
        print(f"Nome: {result.name}")
        print(f"CNPJ: {result.cnpj}")
        print(f"Data: {result.registration_date}")
        
    except CarrierRegistrationError as e:
        print(f"Erro no registro: {e}")