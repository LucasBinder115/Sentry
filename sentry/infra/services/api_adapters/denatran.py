# sentry/infra/services/api_adapters/denatran.py

import logging
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class VehicleStatus(Enum):
    REGULAR = "REGULAR"
    ROUBO = "ROUBO"
    FURTO = "FURTO"
    APREENDIDO = "APREENDIDO"

@dataclass
class VehicleInfo:
    plate: str
    status: VehicleStatus
    model: Optional[str] = None
    color: Optional[str] = None
    restrictions: list = None
    
    def __post_init__(self):
        if self.restrictions is None:
            self.restrictions = []

class DenatranAPIAdapter:
    """Adapter simplificado para API Denatran."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.simulate_mode = not api_key
        logger.info("DenatranAdapter iniciado (modo: %s)", 
                   "simulação" if self.simulate_mode else "produção")
    
    def get_vehicle_info(self, plate: str) -> VehicleInfo:
        """
        Consulta informações do veículo pela placa.
        
        Args:
            plate: Placa do veículo (ABC1D23 ou ABC1234)
            
        Returns:
            VehicleInfo: Informações do veículo
        """
        logger.info("Consultando veículo: %s", plate)
        
        if self.simulate_mode:
            return self._get_simulated_data(plate)
        
        # TODO: Implementar chamada real à API quando tiver chave
        return self._get_simulated_data(plate)
    
    def _get_simulated_data(self, plate: str) -> VehicleInfo:
        """Dados simulados para desenvolvimento."""
        # Simulação simples baseada na placa
        import hashlib
        plate_hash = hashlib.md5(plate.encode()).hexdigest()
        hash_int = int(plate_hash[:8], 16)
        
        # 90% regular, 10% problemas
        status = VehicleStatus.REGULAR
        if hash_int % 10 == 0:  # 10% de chance
            status = VehicleStatus.ROUBO
        elif hash_int % 10 == 1:  # 10% de chance  
            status = VehicleStatus.FURTO
        
        models = ["Gol", "Uno", "Onix", "Ka", "HB20"]
        colors = ["Branco", "Preto", "Prata", "Vermelho"]
        
        restrictions = []
        if status != VehicleStatus.REGULAR:
            restrictions = ["Veículo com restrição de circulação"]
        
        return VehicleInfo(
            plate=plate,
            status=status,
            model=models[hash_int % len(models)],
            color=colors[hash_int % len(colors)],
            restrictions=restrictions
        )

# Fábrica simplificada
def create_denatran_adapter(api_key: Optional[str] = None) -> DenatranAPIAdapter:
    """Cria instância do adapter Denatran."""
    return DenatranAPIAdapter(api_key=api_key)