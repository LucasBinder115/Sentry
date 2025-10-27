# sentry/core/entities/carrier.py

from datetime import datetime, date
from enum import Enum
import re

class CarrierStatus(Enum):
    """Enum para definir o status da transportadora."""
    ACTIVE = "Ativa"
    INACTIVE = "Inativa"
    SUSPENDED = "Suspensa"
    PENDING_DOCUMENTATION = "Pendente de Documentação"

class CarrierType(Enum):
    """Enum para definir o tipo de transporte."""
    GENERAL_CARGO = "Carga Geral"
    REFRIGERATED = "Refrigerado"
    DANGEROUS_GOODS = "Produtos Perigosos"
    LIQUID_BULK = "Granel Líquido"
    SOLID_BULK = "Granel Sólido"
    CONTAINER = "Conteinerizado"

class Carrier:
    """
    Entidade que representa uma Transportadora de forma robusta.
    Contém dados legais, operacionais e de conformidade.
    """
    def __init__(
        self,
        name: str,
        cnpj: str,
        status: CarrierStatus = CarrierStatus.PENDING_DOCUMENTATION,
        carrier_type: CarrierType = CarrierType.GENERAL_CARGO,
        id: int = None,
        responsible_name: str = None,
        responsible_cpf: str = None,
        contact_phone: str = None,
        contact_email: str = None,
        municipal_registration: str = None,
        state_registration: str = None,
        address: str = None,
        city: str = None,
        state: str = None,
        zip_code: str = None,
        created_at: datetime = None,
        updated_at: datetime = None,
        details: dict = None
    ):
        self.id = id
        self.name = name
        self.cnpj = self._validate_cnpj(cnpj)
        self.status = status
        self.carrier_type = carrier_type
        
        # Dados do Responsável Legal
        self.responsible_name = responsible_name
        self.responsible_cpf = responsible_cpf
        
        # Dados de Contato
        self.contact_phone = contact_phone
        self.contact_email = contact_email
        
        # Dados Fiscais e de Endereço
        self.municipal_registration = municipal_registration
        self.state_registration = state_registration
        self.address = address
        self.city = city
        self.state = state
        self.zip_code = zip_code
        
        # Controle de Tempo
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        
        # Campo flexível para detalhes extras
        self.details = details or {}

    def __repr__(self):
        return (f"<Carrier (id={self.id}, name='{self.name}', cnpj='{self.cnpj}', "
                f"status='{self.status.value}')>")

    # --- Métodos de Validação ---

    def _validate_cnpj(self, cnpj: str) -> str:
        """Valida e formata o CNPJ."""
        if not cnpj:
            raise ValueError("CNPJ não pode ser vazio.")
        
        # Remove caracteres não numéricos
        digits = re.sub(r'\D', '', cnpj)
        
        if len(digits) != 14:
            raise ValueError("CNPJ deve conter 14 dígitos.")
        
        # Aqui você poderia adicionar a lógica de validação dos dígitos verificadores
        # Por enquanto, apenas a validação de formato é suficiente.
        return digits

    # --- Métodos de Serialização ---

    def to_dict(self) -> dict:
        """Converte o objeto Carrier para um dicionário."""
        return {
            "id": self.id,
            "name": self.name,
            "cnpj": self.cnpj,
            "status": self.status.value,
            "carrier_type": self.carrier_type.value,
            "responsible_name": self.responsible_name,
            "responsible_cpf": self.responsible_cpf,
            "contact_phone": self.contact_phone,
            "contact_email": self.contact_email,
            "municipal_registration": self.municipal_registration,
            "state_registration": self.state_registration,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "details": self.details
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Carrier':
        """Cria uma instância de Carrier a partir de um dicionário."""
        status = CarrierStatus(data.get("status")) if data.get("status") else CarrierStatus.PENDING_DOCUMENTATION
        carrier_type = CarrierType(data.get("carrier_type")) if data.get("carrier_type") else CarrierType.GENERAL_CARGO
        
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data.get("created_at"))
        
        updated_at = None
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data.get("updated_at"))

        return cls(
            id=data.get("id"),
            name=data.get("name"),
            cnpj=data.get("cnpj"),
            status=status,
            carrier_type=carrier_type,
            responsible_name=data.get("responsible_name"),
            responsible_cpf=data.get("responsible_cpf"),
            contact_phone=data.get("contact_phone"),
            contact_email=data.get("contact_email"),
            municipal_registration=data.get("municipal_registration"),
            state_registration=data.get("state_registration"),
            address=data.get("address"),
            city=data.get("city"),
            state=data.get("state"),
            zip_code=data.get("zip_code"),
            created_at=created_at,
            updated_at=updated_at,
            details=data.get("details", {})
        )

    # --- Métodos de Lógica de Negócio ---

    def activate(self):
        """Ativa a transportadora se estiver pendente."""
        if self.status == CarrierStatus.PENDING_DOCUMENTATION:
            self.status = CarrierStatus.ACTIVE
            self.updated_at = datetime.now()
        else:
            raise ValueError(f"Não é possível ativar uma transportadora com status '{self.status.value}'.")

    def suspend(self, reason: str = None):
        """Suspende a transportadora."""
        if self.status == CarrierStatus.ACTIVE:
            self.status = CarrierStatus.SUSPENDED
            self.updated_at = datetime.now()
            if reason:
                self.details["suspension_reason"] = reason
        else:
            raise ValueError(f"Não é possível suspender uma transportadora com status '{self.status.value}'.")
            
    def is_active(self) -> bool:
        """Verifica se a transportadora está ativa."""
        return self.status == CarrierStatus.ACTIVE

    def get_formatted_cnpj(self) -> str:
        """Retorna o CNPJ formatado (XX.XXX.XXX/XXXX-XX)."""
        if not self.cnpj or len(self.cnpj) != 14:
            return self.cnpj
        return f"{self.cnpj[:2]}.{self.cnpj[2:5]}.{self.cnpj[5:8]}/{self.cnpj[8:12]}-{self.cnpj[12:14]}"

    def can_transport_dangerous_goods(self) -> bool:
        """Verifica se a transportadora tem o tipo para transportar produtos perigosos."""
        return self.carrier_type == CarrierType.DANGEROUS_GOODS
