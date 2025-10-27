# sentry/core/use_cases/process_vehicle_access.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from sentry.core.use_cases.plate_recognition_system import PlateRecognitionSystem, PlateRecognitionResult
from sentry.infra.services.denatran import DenatranAPIAdapter, DenatranAdapterFactory
from sentry.infra.database.repositories.vehicle_movement_repo import VehicleMovementRepository
from sentry.core.entities.access_log import AccessLog

logger = logging.getLogger(__name__)


class VehicleAccessProcessor:
    """
    Processador completo de acesso de veículos.
    
    Integra:
    - Reconhecimento de placas (YOLOv8 + OCR)
    - Consulta Denatran
    - Registro no banco de dados
    """
    
    def __init__(
        self,
        plate_system: Optional[PlateRecognitionSystem] = None,
        denatran_adapter: Optional[DenatranAPIAdapter] = None,
        movement_repo: Optional[VehicleMovementRepository] = None
    ):
        self.plate_system = plate_system or PlateRecognitionSystem()
        self.denatran_adapter = denatran_adapter or DenatranAdapterFactory.create_simulation_adapter()
        self.movement_repo = movement_repo or VehicleMovementRepository()
        
        logger.info("VehicleAccessProcessor inicializado")
    
    def process_vehicle_access(self, image_path: Path, gate_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa acesso completo de um veículo.
        
        Args:
            image_path: Caminho da imagem do veículo
            gate_info: Informações do portão/faixa
            
        Returns:
            Dict com resultados completos do processamento
        """
        start_time = datetime.now()
        
        logger.info(f"Processando acesso do veículo: {image_path}")
        
        try:
            # 1. Reconhecimento da placa
            plate_results = self.plate_system.process_image(image_path)
            
            if not plate_results:
                return {
                    'success': False,
                    'error': 'Nenhuma placa detectada',
                    'processing_time': (datetime.now() - start_time).total_seconds()
                }
            
            # Pega o resultado com maior confiança
            best_result = max(plate_results, key=lambda x: x.confidence)
            plate_text = best_result.plate_text
            
            # 2. Consulta Denatran
            denatran_info = self.denatran_adapter.consult_vehicle(plate_text)
            
            # 3. Registra acesso
            access_log = AccessLog(
                vehicle_plate=plate_text,
                timestamp=datetime.now(),
                vehicle_type=gate_info.get('vehicle_type'),
                driver_name=gate_info.get('driver_name'),
                carrier_name=gate_info.get('carrier_name'),
                access_type=gate_info.get('access_type', 'entry'),
                gate_number=gate_info.get('gate_number'),
                lane_number=gate_info.get('lane_number'),
                security_alert=denatran_info.theft_indicator or denatran_info.robbery_indicator,
                alert_reason="Veículo com indicativo de roubo/furto" if denatran_info.theft_indicator else None
            )
            
            saved_log = self.movement_repo.save(access_log)
            
            # 4. Prepara resultado
            result = {
                'success': True,
                'plate_text': plate_text,
                'confidence': best_result.confidence,
                'denatran_status': denatran_info.status.value,
                'security_alert': denatran_info.theft_indicator or denatran_info.robbery_indicator,
                'log_id': saved_log.id,
                'processing_time': (datetime.now() - start_time).total_seconds(),
                'detection_details': {
                    'bounding_box': best_result.detection_metadata['bounding_box'],
                    'detection_confidence': best_result.detection_metadata['detection_confidence']
                },
                'denatran_details': {
                    'brand': denatran_info.brand,
                    'model': denatran_info.model,
                    'color': denatran_info.color,
                    'restrictions': denatran_info.restrictions
                }
            }
            
            logger.info(f"Acesso processado: {plate_text} (Status: {denatran_info.status.value})")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro no processamento do acesso: {e}")
            return {
                'success': False,
                'error': str(e),
                'processing_time': (datetime.now() - start_time).total_seconds()
            }