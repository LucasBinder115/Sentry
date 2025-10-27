# sentry/core/entities/merchandise.py

from datetime import datetime, date
from enum import Enum
from typing import Optional

class MerchandiseType(Enum):
    """Enum para classificar o tipo da mercadoria."""
    GENERAL = "Carga Geral"
    FOOD = "Alimentos"
    ELECTRONICS = "Eletrônicos"
    TEXTILES = "Têxteis"
    DANGEROUS_GOODS = "Produtos Perigosos"
    LIQUID = "Líquidos"
    PHARMACEUTICAL = "Farmacêutico"

class MerchandiseStatus(Enum):
    """Enum para definir o status da mercadoria na cadeia logística."""
    REGISTERED = "Registrado"
    PENDING_PICKUP = "Pendente de Coleta"
    IN_TRANSIT = "Em Trânsito"
    DELIVERED = "Entregue"
    DELAYED = "Atrasado"
    LOST = "Perdida"
    DAMAGED = "Danificada"

class TemperatureControl(Enum):
    """Enum para exigência de controle de temperatura."""
    NONE = "Ambiente"
    REFRIGERATED = "Refrigerado"
    FROZEN = "Congelado"
    CLIMATE_CONTROLLED = "Climatizado"

class Merchandise:
    """
    Entidade que representa uma mercadoria de forma robusta.
    Contém dados operacionais, fiscais e de rastreamento.
    """
    def __init__(
        self,
        description: str,
        merchandise_type: MerchandiseType,
        status: MerchandiseStatus = MerchandiseStatus.REGISTERED,
        id: int = None,
        tracking_code: str = None,
        invoice_number: str = None,
        invoice_key: str = None, # Chave de acesso da NFe
        weight: float = None,
        volume: float = None,
        unit_of_measure: str = "KG/M³", # Ex: KG, M³, UNIDADES
        quantity: int = 1,
        unit_value: float = None,
        total_value: float = None,
        temperature_control: TemperatureControl = TemperatureControl.NONE,
        is_dangerous: bool = False,
        hazard_class: str = None, # Ex: "Classe 3 - Líquidos Inflamáveis"
        
        # Relacionamentos (IDs)
        vehicle_id: int = None, # ID do veículo que transportará
        carrier_id: int = None, # ID da transportadora responsável
        sender_id: int = None, # ID do remetente (pessoa/empresa)
        recipient_id: int = None, # ID do destinatário (pessoa/empresa)
        
        # Dados de Rastreamento
        origin_city: str = None,
        destination_city: str = None,
        estimated_delivery_date: date = None,
        actual_delivery_date: date = None,
        
        # Metadados
        created_at: datetime = None,
        updated_at: datetime = None,
        notes: str = None,
        details: dict = None
    ):
        self.id = id
        self.description = description
        self.merchandise_type = merchandise_type
        self.status = status
        
        # Dados Fiscais
        self.tracking_code = tracking_code
        self.invoice_number = invoice_number
        self.invoice_key = invoice_key
        
        # Dados Físicos
        self.weight = weight
        self.volume = volume
        self.unit_of_measure = unit_of_measure
        self.quantity = quantity
        self.unit_value = unit_value
        self.total_value = total_value or (quantity * unit_value if unit_value else None)
        
        # Dados de Manuseio e Segurança
        self.temperature_control = temperature_control
        self.is_dangerous = is_dangerous
        self.hazard_class = hazard_class if is_dangerous else None
        
        # Relacionamentos
        self.vehicle_id = vehicle_id
        self.carrier_id = carrier_id
        self.sender_id = sender_id
        self.recipient_id = recipient_id
        
        # Dados de Rastreamento
        self.origin_city = origin_city
        self.destination_city = destination_city
        self.estimated_delivery_date = estimated_delivery_date
        self.actual_delivery_date = actual_delivery_date
        
        # Controle de Tempo
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        
        # Campos de texto livre
        self.notes = notes
        self.details = details or {}

    def __repr__(self):
        return (f"<Merchandise (id={self.id}, description='{self.description}', "
                f"status='{self.status.value}', tracking='{self.tracking_code}')>")

    # --- Métodos de Serialização ---

    def to_dict(self) -> dict:
        """Converte o objeto Merchandise para um dicionário."""
        return {
            "id": self.id,
            "description": self.description,
            "merchandise_type": self.merchandise_type.value,
            "status": self.status.value,
            "tracking_code": self.tracking_code,
            "invoice_number": self.invoice_number,
            "invoice_key": self.invoice_key,
            "weight": self.weight,
            "volume": self.volume,
            "unit_of_measure": self.unit_of_measure,
            "quantity": self.quantity,
            "unit_value": self.unit_value,
            "total_value": self.total_value,
            "temperature_control": self.temperature_control.value,
            "is_dangerous": self.is_dangerous,
            "hazard_class": self.hazard_class,
            "vehicle_id": self.vehicle_id,
            "carrier_id": self.carrier_id,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "origin_city": self.origin_city,
            "destination_city": self.destination_city,
            "estimated_delivery_date": self.estimated_delivery_date.isoformat() if self.estimated_delivery_date else None,
            "actual_delivery_date": self.actual_delivery_date.isoformat() if self.actual_delivery_date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "notes": self.notes,
            "details": self.details
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Merchandise':
        """Cria uma instância de Merchandise a partir de um dicionário."""
        merchandise_type = MerchandiseType(data.get("merchandise_type")) if data.get("merchandise_type") else MerchandiseType.GENERAL
        status = MerchandiseStatus(data.get("status")) if data.get("status") else MerchandiseStatus.REGISTERED
        temp_control = TemperatureControl(data.get("temperature_control")) if data.get("temperature_control") else TemperatureControl.NONE

        est_date = None
        if data.get("estimated_delivery_date"):
            est_date = date.fromisoformat(data.get("estimated_delivery_date"))
        
        act_date = None
        if data.get("actual_delivery_date"):
            act_date = date.fromisoformat(data.get("actual_delivery_date"))

        created_at = datetime.fromisoformat(data.get("created_at")) if data.get("created_at") else datetime.now()
        updated_at = datetime.fromisoformat(data.get("updated_at")) if data.get("updated_at") else datetime.now()

        return cls(
            id=data.get("id"),
            description=data.get("description"),
            merchandise_type=merchandise_type,
            status=status,
            tracking_code=data.get("tracking_code"),
            invoice_number=data.get("invoice_number"),
            invoice_key=data.get("invoice_key"),
            weight=data.get("weight"),
            volume=data.get("volume"),
            unit_of_measure=data.get("unit_of_measure"),
            quantity=data.get("quantity"),
            unit_value=data.get("unit_value"),
            total_value=data.get("total_value"),
            temperature_control=temp_control,
            is_dangerous=data.get("is_dangerous", False),
            hazard_class=data.get("hazard_class"),
            vehicle_id=data.get("vehicle_id"),
            carrier_id=data.get("carrier_id"),
            sender_id=data.get("sender_id"),
            recipient_id=data.get("recipient_id"),
            origin_city=data.get("origin_city"),
            destination_city=data.get("destination_city"),
            estimated_delivery_date=est_date,
            actual_delivery_date=act_date,
            created_at=created_at,
            updated_at=updated_at,
            notes=data.get("notes"),
            details=data.get("details", {})
        )

    # --- Métodos de Lógica de Negócio ---

    def mark_as_in_transit(self, vehicle_id: int):
        """Marca a mercadoria como 'Em Trânsito'."""
        if self.status == MerchandiseStatus.PENDING_PICKUP:
            self.status = MerchandiseStatus.IN_TRANSIT
            self.vehicle_id = vehicle_id
            self.updated_at = datetime.now()
        else:
            raise ValueError(f"Mercadoria não pode ser marcada como 'Em Trânsito' com status '{self.status.value}'.")

    def mark_as_delivered(self):
        """Marca a mercadoria como 'Entregue'."""
        if self.status == MerchandiseStatus.IN_TRANSIT:
            self.status = MerchandiseStatus.DELIVERED
            self.actual_delivery_date = date.today()
            self.updated_at = datetime.now()
        else:
            raise ValueError(f"Mercadoria não pode ser marcada como 'Entregue' com status '{self.status.value}'.")

    def is_delayed(self) -> bool:
        """Verifica se a entrega está atrasada com base na data estimada."""
        if self.estimated_delivery_date and self.status not in [MerchandiseStatus.DELIVERED, MerchandiseStatus.LOST]:
            return date.today() > self.estimated_delivery_date
        return False

    def is_ready_for_transport(self, carrier_repo) -> bool:
        """
        Verifica se a mercadoria está pronta para o transporte,
        validando a transportadora compatível.
        """
        if self.carrier_id is None:
            return False # Não há transportadora associada

        # Aqui você injetaria o repositório de transportadoras
        # carrier = carrier_repo.find_by_id(self.carrier_id)
        # if not carrier or not carrier.is_active():
        #     return False

        # Validação de compatibilidade (ex: produtos perigosos)
        # if self.is_dangerous and not carrier.can_transport_dangerous_goods():
        #     return False
        
        # Validação de controle de temperatura
        # if self.temperature_control != TemperatureControl.NONE and not carrier.has_refrigerated_trucks():
        #     return False

        return True # Simplificado para o exemplo