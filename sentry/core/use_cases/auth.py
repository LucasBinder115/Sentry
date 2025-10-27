import logging
import re
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

# Configuração básica de log
logger = logging.getLogger(__name__)


# Exceções customizadas
class UserNotFoundError(Exception):
    """Exceção lançada quando usuário não é encontrado."""
    pass


class InvalidCredentialsError(Exception):
    """Exceção lançada quando credenciais são inválidas."""
    pass


class CPFValidationError(Exception):
    """Exceção lançada quando há erro específico na validação do CPF."""
    pass


@dataclass
class UserInfo:
    """Classe para representar informações do usuário de forma estruturada."""
    id: int
    email: str
    role: str


class CPFValidator:
    """Classe dedicada para validação de CPF com métodos auxiliares."""
    
    @staticmethod
    def clean_cpf(cpf: str) -> str:
        """
        Remove caracteres não numéricos do CPF.
        
        Args:
            cpf: CPF a ser limpo
            
        Returns:
            CPF contendo apenas dígitos
        """
        return ''.join(filter(str.isdigit, cpf))
    
    @staticmethod
    def is_sequential(cpf: str) -> bool:
        """
        Verifica se o CPF é uma sequência de números iguais.
        
        Args:
            cpf: CPF a ser verificado
            
        Returns:
            True se for sequência, False caso contrário
        """
        return len(set(cpf)) == 1
    
    @staticmethod
    def calculate_verification_digit(cpf_partial: str, weight_start: int) -> int:
        """
        Calcula dígito verificador do CPF.
        
        Args:
            cpf_partial: Parte do CPF para cálculo
            weight_start: Peso inicial para multiplicação
            
        Returns:
            Dígito verificador calculado
        """
        total = sum(int(digit) * (weight_start - index) 
                   for index, digit in enumerate(cpf_partial))
        remainder = total % 11
        return 0 if remainder < 2 else 11 - remainder
    
    @classmethod
    def validate_cpf_structure(cls, cpf: str) -> Tuple[bool, str]:
        """
        Valida estrutura básica do CPF.
        
        Args:
            cpf: CPF a ser validado
            
        Returns:
            Tuple (is_valid, cleaned_cpf)
        """
        cleaned_cpf = cls.clean_cpf(cpf)
        
        if len(cleaned_cpf) != 11:
            return False, cleaned_cpf
            
        if not cleaned_cpf.isdigit():
            return False, cleaned_cpf
            
        if cls.is_sequential(cleaned_cpf):
            return False, cleaned_cpf
            
        return True, cleaned_cpf
    
    @classmethod
    def validate_cpf_digits(cls, cpf: str) -> bool:
        """
        Valida dígitos verificadores do CPF.
        
        Args:
            cpf: CPF a ser validado (já limpo)
            
        Returns:
            True se dígitos verificadores são válidos
        """
        # Primeiro dígito verificador
        first_digit = cls.calculate_verification_digit(cpf[:9], 10)
        if first_digit != int(cpf[9]):
            return False
        
        # Segundo dígito verificador
        second_digit = cls.calculate_verification_digit(cpf[:10], 11)
        return second_digit == int(cpf[10])
    
    @classmethod
    def is_valid_cpf(cls, cpf: str) -> bool:
        """
        Valida o CPF de forma completa.
        
        Args:
            cpf: CPF a ser validado
            
        Returns:
            True se CPF é válido
        """
        try:
            is_valid_structure, cleaned_cpf = cls.validate_cpf_structure(cpf)
            if not is_valid_structure:
                return False
                
            return cls.validate_cpf_digits(cleaned_cpf)
            
        except Exception as e:
            logger.error(f"[CPF Validation] Erro inesperado na validação: {e}")
            return False


class EmailValidator:
    """Classe para validação de email."""
    
    EMAIL_REGEX = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    @classmethod
    def is_valid_email(cls, email: str) -> bool:
        """
        Valida formato do email.
        
        Args:
            email: Email a ser validado
            
        Returns:
            True se email é válido
        """
        if not email or not isinstance(email, str):
            return False
            
        return bool(cls.EMAIL_REGEX.match(email.strip()))


class InputValidator:
    """Classe para validação de entradas do usuário."""
    
    @staticmethod
    def validate_inputs(email: str, cpf: str) -> None:
        """
        Valida as entradas básicas antes do processamento.
        
        Args:
            email: Email do usuário
            cpf: CPF do usuário
            
        Raises:
            InvalidCredentialsError: Se as entradas forem inválidas
        """
        if not email or not isinstance(email, str):
            raise InvalidCredentialsError("Email não pode estar vazio")
            
        if not cpf or not isinstance(cpf, str):
            raise InvalidCredentialsError("CPF não pode estar vazio")
            
        if not EmailValidator.is_valid_email(email):
            raise InvalidCredentialsError("Formato de email inválido")
        
        # Validação básica do CPF (apenas estrutura)
        is_valid_structure, _ = CPFValidator.validate_cpf_structure(cpf)
        if not is_valid_structure:
            raise InvalidCredentialsError("Formato de CPF inválido")


class AuthUseCase:
    def __init__(self, user_repo, max_login_attempts: int = 5):
        self.user_repo = user_repo
        self.max_login_attempts = max_login_attempts
        self.login_attempts: Dict[str, int] = {}
        
    def _check_login_attempts(self, email: str) -> None:
        """
        Verifica se o usuário excedeu o número máximo de tentativas.
        
        Args:
            email: Email do usuário
            
        Raises:
            InvalidCredentialsError: Se excedeu o limite de tentativas
        """
        attempts = self.login_attempts.get(email, 0)
        if attempts >= self.max_login_attempts:
            logger.warning("[Auth] Muitas tentativas de login para: %s", email)
            raise InvalidCredentialsError(
                "Número máximo de tentativas excedido. Tente novamente mais tarde."
            )
    
    def _reset_login_attempts(self, email: str) -> None:
        """Reseta o contador de tentativas para um email."""
        self.login_attempts.pop(email, None)
    
    def _increment_login_attempts(self, email: str) -> None:
        """Incrementa o contador de tentativas para um email."""
        self.login_attempts[email] = self.login_attempts.get(email, 0) + 1

    def authenticate(self, email: str, cpf: str) -> Dict[str, str | int]:
        """
        Autentica o usuário com base em email e CPF.

        Args:
            email: Email do usuário
            cpf: CPF do usuário

        Returns:
            dict: {"id": int, "username": str, "role": str}

        Raises:
            InvalidCredentialsError: Se as credenciais forem inválidas
            UserNotFoundError: Se o usuário não for encontrado
        """
        logger.info("[Auth] Iniciando autenticação para email=%s", email)
        
        try:
            # Validação inicial das entradas
            InputValidator.validate_inputs(email, cpf)
            
            # Verifica tentativas de login
            self._check_login_attempts(email)
            
            # Validação completa do CPF
            if not CPFValidator.is_valid_cpf(cpf):
                self._increment_login_attempts(email)
                logger.warning("[Auth] CPF inválido: %s", cpf)
                raise InvalidCredentialsError("O CPF informado é inválido.")

            # Busca usuário no repositório
            user = self.user_repo.find_by_email_and_cpf(email, cpf)
            if not user:
                self._increment_login_attempts(email)
                logger.warning("[Auth] Usuário não encontrado: %s", email)
                raise UserNotFoundError("Usuário não encontrado com as credenciais fornecidas.")

            # Login bem-sucedido - reseta tentativas
            self._reset_login_attempts(email)
            logger.info("[Auth] Autenticação bem-sucedida: %s", email)
            
            return {
                "id": user.id,
                "username": user.email,
                "role": user.role,
            }
            
        except (InvalidCredentialsError, UserNotFoundError):
            # Re-lança exceções específicas de autenticação
            raise
        except Exception as e:
            # Log para erros inesperados
            logger.error("[Auth] Erro inesperado durante autenticação: %s", str(e))
            raise InvalidCredentialsError("Erro durante a autenticação")

    def get_login_attempts(self, email: str) -> int:
        """
        Retorna o número de tentativas de login para um email.
        
        Args:
            email: Email do usuário
            
        Returns:
            Número de tentativas
        """
        return self.login_attempts.get(email, 0)


# Exemplo de uso com injeção de dependência
class UserRepository:
    """Exemplo de repositório de usuário (deve ser implementado conforme necessidade)."""
    
    def find_by_email_and_cpf(self, email: str, cpf: str) -> Optional[UserInfo]:
        """
        Busca usuário por email e CPF.
        
        Args:
            email: Email do usuário
            cpf: CPF do usuário
            
        Returns:
            UserInfo se encontrado, None caso contrário
        """
        # Implementação real iria buscar no banco de dados
        # Esta é uma implementação de exemplo
        return None


# Testes unitários básicos (exemplo)
if __name__ == "__main__":
    # Configurar logging para testes
    logging.basicConfig(level=logging.INFO)
    
    # Teste do validador de CPF
    test_cpfs = [
        "529.982.247-25",  # Válido
        "111.111.111-11",  # Inválido (sequência)
        "123.456.789-00",  # Inválido (dígitos)
        "52998224725",     # Válido (sem máscara)
    ]
    
    for cpf in test_cpfs:
        is_valid = CPFValidator.is_valid_cpf(cpf)
        print(f"CPF {cpf}: {'Válido' if is_valid else 'Inválido'}")