# sentry/core/entities/access_log.py

from datetime import datetime
from enum import Enum
import json

class AccessDirection(Enum):
    """Enum para definir a direção do acesso."""
    ENTRY = "Entrada"
    EXIT = "Saída"

class AccessType(Enum):
    """Enum para definir o tipo de acesso."""
    REGISTERED_VEHICLE = "Veículo Registrado"
    UNREGISTERED_VEHICLE = "Veículo Não Registrado"
    PEDESTRIAN = "Pedestre"
    DELIVERY = "Entrega"
    EMERGENCY = "Emergência"

class AccessStatus(Enum):
    """Enum para definir o status do acesso."""
    AUTHORIZED = "Autorizado"
    DENIED = "Negado"
    PENDING = "Pendente Análise"

class AccessLog:
    """
    Entidade que representa um registro de acesso completo e robusto.
    Contém dados sobre o veículo, motorista, localização e mídia do evento.
    """
    def __init__(
        self,
        vehicle_plate: str,
        direction: AccessDirection,
        access_type: AccessType,
        status: AccessStatus,
        timestamp: datetime = None,
        id: int = None,
        driver_name: str = None,
        driver_cpf: str = None,
        carrier_name: str = None,
        gate_id: str = None,
        lane_id: str = None,
        ocr_confidence: float = None,
        photo_path: str = None,
        snapshot_path: str = None,
        matched_vehicle_id: int = None,
        details: dict = None
    ):
        self.id = id
        self.vehicle_plate = vehicle_plate.upper() if vehicle_plate else None
        self.direction = direction
        self.access_type = access_type
        self.status = status
        self.timestamp = timestamp or datetime.now()
        
        # Dados do Motorista/Responsável
        self.driver_name = driver_name
        self.driver_cpf = driver_cpf
        
        # Dados Logísticos
        self.carrier_name = carrier_name
        
        # Dados de Localização Física
        self.gate_id = gate_id  # Ex: "Portão 1", "Portaria Principal"
        self.lane_id = lane_id    # Ex: "Canaleta 1", "Saída de Emergência"
        
        # Metadados da Leitura
        self.ocr_confidence = ocr_confidence  # Ex: 0.95 (95% de confiança)
        
        # Mídia (Caminhos para arquivos)
        self.photo_path = photo_path      # Foto da câmera
        self.snapshot_path = snapshot_path # Snapshot do vídeo com a placa recortada
        
        # Relacionamentos
        self.matched_vehicle_id = matched_vehicle_id # ID do veículo na tabela 'vehicles'
        
        # Campo flexível para detalhes extras (em formato JSON)
        self.details = details or {}

    def __repr__(self):
        return (f"<AccessLog (id={self.id}, plate='{self.vehicle_plate}', "
                f"direction='{self.direction.value}', status='{self.status.value}', "
                f"time='{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}')>")

    def to_dict(self) -> dict:
        """
        Converte o objeto AccessLog para um dicionário.
        Útil para serialização (JSON) e para enviar para a UI.
        """
        return {
            "id": self.id,
            "vehicle_plate": self.vehicle_plate,
            "direction": self.direction.value,
            "access_type": self.access_type.value,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "driver_name": self.driver_name,
            "driver_cpf": self.driver_cpf,
            "carrier_name": self.carrier_name,
            "gate_id": self.gate_id,
            "lane_id": self.lane_id,
            "ocr_confidence": self.ocr_confidence,
            "photo_path": self.photo_path,
            "snapshot_path": self.snapshot_path,
            "matched_vehicle_id": self.matched_vehicle_id,
            "details": self.details
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'AccessLog':
        """
        Cria uma instância de AccessLog a partir de um dicionário.
        Útil para desserializar dados do banco de dados ou de uma API.
        """
        # Converte strings de volta para Enums
        direction = AccessDirection(data.get("direction")) if data.get("direction") else None
        access_type = AccessType(data.get("access_type")) if data.get("access_type") else None
        status = AccessStatus(data.get("status")) if data.get("status") else None
        
        # Converte string ISO de volta para datetime
        timestamp = None
        if data.get("timestamp"):
            timestamp = datetime.fromisoformat(data.get("timestamp"))

        return cls(
            id=data.get("id"),
            vehicle_plate=data.get("vehicle_plate"),
            direction=direction,
            access_type=access_type,
            status=status,
            timestamp=timestamp,
            driver_name=data.get("driver_name"),
            driver_cpf=data.get("driver_cpf"),
            carrier_name=data.get("carrier_name"),
            gate_id=data.get("gate_id"),
            lane_id=data.get("lane_id"),
            ocr_confidence=data.get("ocr_confidence"),
            photo_path=data.get("photo_path"),
            snapshot_path=data.get("snapshot_path"),
            matched_vehicle_id=data.get("matched_vehicle_id"),
            details=data.get("details", {})
        )

    def get_duration_in_minutes(self, exit_log: 'AccessLog') -> int | None:
        """
        Calcula a duração em minutos entre este log (de entrada) e um log de saída.
        Retorna None se os horários forem inválidos.
        """
        if not isinstance(exit_log, AccessLog) or self.direction != AccessDirection.ENTRY or exit_log.direction != AccessDirection.EXIT:
            return None
        
        if self.timestamp and exit_log.timestamp:
            delta = exit_log.timestamp - self.timestamp
            return int(delta.total_seconds() / 60)
        return None
