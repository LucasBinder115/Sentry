# sentry/core/use_cases/plate_recognition_system.py

import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

from sentry.infra.services.yolov8_detector import YOLOv8PlateDetector, PlateDetectorFactory
from sentry.infra.services.ocr_service import OcrService, OcrServiceFactory
from sentry.infra.services.camera_adapter import CameraAdapter, CameraAdapterFactory

# Configuração de logging
logger = logging.getLogger(__name__)


@dataclass
class PlateRecognitionResult:
    """Resultado completo do reconhecimento de placa."""
    plate_text: str
    confidence: float
    bounding_box: Any
    processing_time: float
    image_path: Path
    timestamp: datetime
    detection_metadata: Dict[str, Any]
    ocr_metadata: Dict[str, Any]
    camera_metadata: Dict[str, Any]


class PlateRecognitionSystem:
    """
    Sistema integrado de reconhecimento de placas.
    
    Combina:
    - YOLOv8 para detecção de placas
    - OCR para leitura do texto
    - Câmera para captura de imagens
    """
    
    def __init__(
        self,
        plate_detector: Optional[YOLOv8PlateDetector] = None,
        ocr_service: Optional[OcrService] = None,
        camera_adapter: Optional[CameraAdapter] = None
    ):
        self.plate_detector = plate_detector or PlateDetectorFactory.create_default_detector()
        self.ocr_service = ocr_service or OcrServiceFactory.create_default_service()
        self.camera_adapter = camera_adapter or CameraAdapterFactory.create_default_adapter()
        
        logger.info("Sistema de Reconhecimento de Placas inicializado")
    
    def process_image(self, image_path: Path) -> List[PlateRecognitionResult]:
        """
        Processa uma imagem para reconhecimento de placas.
        
        Args:
            image_path: Caminho para a imagem
            
        Returns:
            Lista de resultados de reconhecimento
        """
        start_time = datetime.now()
        
        logger.info(f"Processando imagem para reconhecimento de placas: {image_path}")
        
        try:
            # 1. Detecção de placas com YOLOv8
            detection_result = self.plate_detector.detect_plates(image_path)
            
            if not detection_result.success or not detection_result.bounding_boxes:
                logger.warning("Nenhuma placa detectada na imagem")
                return []
            
            results = []
            
            # 2. Para cada placa detectada, extrai região e faz OCR
            plate_regions = self.plate_detector.extract_plate_regions(image_path)
            
            for bbox, plate_region in plate_regions:
                # Salva região temporária para OCR
                temp_plate_path = Path(f"temp_plate_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg")
                try:
                    # Converte para BGR e salva
                    plate_region_bgr = plate_region if len(plate_region.shape) == 3 else cv2.cvtColor(plate_region, cv2.COLOR_RGB2BGR)
                    cv2.imwrite(str(temp_plate_path), plate_region_bgr)
                    
                    # 3. Reconhecimento de texto com OCR
                    ocr_result = self.ocr_service.read_plate_from_image(str(temp_plate_path))
                    
                    # 4. Combina resultados
                    recognition_result = PlateRecognitionResult(
                        plate_text=ocr_result.plate_text,
                        confidence=ocr_result.confidence * bbox.confidence,  # Combina confianças
                        bounding_box=bbox,
                        processing_time=(datetime.now() - start_time).total_seconds(),
                        image_path=image_path,
                        timestamp=datetime.now(),
                        detection_metadata={
                            'detection_confidence': bbox.confidence,
                            'bounding_box': (bbox.x1, bbox.y1, bbox.x2, bbox.y2),
                            'region_size': (bbox.width, bbox.height)
                        },
                        ocr_metadata=ocr_result.metadata,
                        camera_metadata={}
                    )
                    
                    results.append(recognition_result)
                    
                finally:
                    # Limpa arquivo temporário
                    if temp_plate_path.exists():
                        temp_plate_path.unlink()
            
            logger.info(f"Reconhecimento concluído: {len(results)} placas reconhecidas")
            return results
            
        except Exception as e:
            logger.error(f"Erro no processamento da imagem: {e}")
            return []
    
    def capture_and_process(self, output_dir: Path = None) -> List[PlateRecognitionResult]:
        """
        Captura imagem da câmera e processa para reconhecimento.
        
        Args:
            output_dir: Diretório para salvar imagens capturadas
            
        Returns:
            Lista de resultados de reconhecimento
        """
        if output_dir is None:
            output_dir = Path("data/captures")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # 1. Captura imagem da câmera
            capture_result = self.camera_adapter.capture_frame()
            
            if not capture_result.success or capture_result.frame is None:
                logger.error("Falha na captura da câmera")
                return []
            
            # 2. Salva imagem temporária
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            temp_image_path = output_dir / f"capture_{timestamp}.jpg"
            
            # Converte e salva
            if len(capture_result.frame.shape) == 3:
                image_bgr = cv2.cvtColor(capture_result.frame, cv2.COLOR_RGB2BGR)
            else:
                image_bgr = capture_result.frame
            
            cv2.imwrite(str(temp_image_path), image_bgr)
            
            # 3. Processa imagem
            results = self.process_image(temp_image_path)
            
            # 4. Adiciona metadados da câmera
            for result in results:
                result.camera_metadata = capture_result.metadata
            
            logger.info(f"Captura e processamento concluídos: {len(results)} placas reconhecidas")
            
            return results
            
        except Exception as e:
            logger.error(f"Erro na captura e processamento: {e}")
            return []
    
    def batch_process(self, image_paths: List[Path]) -> Dict[Path, List[PlateRecognitionResult]]:
        """
        Processa múltiplas imagens em lote.
        
        Args:
            image_paths: Lista de caminhos de imagens
            
        Returns:
            Dicionário com resultados por imagem
        """
        results = {}
        
        for image_path in image_paths:
            try:
                image_results = self.process_image(image_path)
                results[image_path] = image_results
            except Exception as e:
                logger.warning(f"Erro no processamento de {image_path}: {e}")
                results[image_path] = []
        
        total_plates = sum(len(r) for r in results.values())
        logger.info(f"Processamento em lote concluído: {len(image_paths)} imagens, {total_plates} placas")
        
        return results
    
    def get_system_status(self) -> Dict[str, Any]:
        """Retorna status de todos os componentes do sistema."""
        return {
            'plate_detector': self.plate_detector.get_model_info(),
            'ocr_service': {
                'status': 'active',
                'engine': getattr(self.ocr_service.config, 'engine', 'unknown').value
            },
            'camera_adapter': self.camera_adapter.get_camera_info(),
            'timestamp': datetime.now().isoformat()
        }