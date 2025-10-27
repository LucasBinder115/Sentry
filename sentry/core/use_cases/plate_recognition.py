# LOGISICA/sentry/core/use_cases/plate_recognition.py

import os
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import cv2
import numpy as np

# Configuração de logging
logger = logging.getLogger(__name__)


# Exceções customizadas
class PlateRecognitionError(Exception):
    """Exceção base para erros de reconhecimento de placas."""
    pass


class InvalidImageError(PlateRecognitionError):
    """Exceção para imagem inválida ou corrompida."""
    pass


class NoPlateDetectedError(PlateRecognitionError):
    """Exceção quando nenhuma placa é detectada na imagem."""
    pass


class LowConfidenceError(PlateRecognitionError):
    """Exceção quando a confiança do reconhecimento é baixa."""
    pass


class UnsupportedImageFormatError(PlateRecognitionError):
    """Exceção para formato de imagem não suportado."""
    pass


class PlateType(Enum):
    """Tipos de placas de veículos suportados."""
    MERCOSUL = "mercosul"
    BRASIL_ANTIGO = "brasil_antigo"
    UNKNOWN = "unknown"


@dataclass
class PlateRegion:
    """Região da placa detectada na imagem."""
    x: int
    y: int
    width: int
    height: int
    confidence: float


@dataclass
class PlateRecognitionResult:
    """Resultado do reconhecimento de placa."""
    plate_text: str
    confidence: float
    plate_type: PlateType
    plate_region: PlateRegion
    processing_time: float
    image_path: str
    metadata: Dict[str, Any]
    timestamp: datetime


@dataclass
class PlateRecognitionConfig:
    """Configurações para reconhecimento de placas."""
    min_confidence: float = 0.7
    max_image_size: Tuple[int, int] = (1920, 1080)
    supported_formats: Tuple[str] = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    preprocess_image: bool = True
    enhance_contrast: bool = True
    debug_mode: bool = False
    output_dir: str = "data/plate_recognition"


class ImagePreprocessor:
    """Pré-processador de imagens para otimizar reconhecimento."""
    
    @staticmethod
    def validate_image(image_path: str) -> bool:
        """
        Valida se o arquivo de imagem é válido e suportado.
        
        Args:
            image_path: Caminho para a imagem
            
        Returns:
            True se a imagem é válida
        """
        if not os.path.exists(image_path):
            raise InvalidImageError(f"Arquivo não encontrado: {image_path}")
        
        file_ext = Path(image_path).suffix.lower()
        if file_ext not in PlateRecognitionConfig().supported_formats:
            raise UnsupportedImageFormatError(
                f"Formato não suportado: {file_ext}. "
                f"Formatos suportados: {PlateRecognitionConfig().supported_formats}"
            )
        
        try:
            img = cv2.imread(image_path)
            if img is None:
                raise InvalidImageError("Não foi possível carregar a imagem")
            return True
        except Exception as e:
            raise InvalidImageError(f"Erro ao carregar imagem: {e}")
    
    @staticmethod
    def load_and_preprocess(image_path: str, config: PlateRecognitionConfig) -> np.ndarray:
        """
        Carrega e pré-processa a imagem para reconhecimento.
        
        Args:
            image_path: Caminho para a imagem
            config: Configurações de processamento
            
        Returns:
            Imagem pré-processada
        """
        # Carrega imagem
        img = cv2.imread(image_path)
        if img is None:
            raise InvalidImageError("Falha ao carregar imagem")
        
        # Redimensiona se necessário
        height, width = img.shape[:2]
        max_width, max_height = config.max_image_size
        
        if width > max_width or height > max_height:
            scale = min(max_width / width, max_height / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height))
        
        if config.preprocess_image:
            img = ImagePreprocessor._enhance_image(img, config)
        
        return img
    
    @staticmethod
    def _enhance_image(img: np.ndarray, config: PlateRecognitionConfig) -> np.ndarray:
        """
        Aplica técnicas de enhancement na imagem.
        
        Args:
            img: Imagem original
            config: Configurações
            
        Returns:
            Imagem melhorada
        """
        # Converte para escala de cinza
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        if config.enhance_contrast:
            # Aplica CLAHE para melhorar contraste
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
        
        # Redução de ruído
        gray = cv2.medianBlur(gray, 3)
        
        return gray


class PlateDetector(ABC):
    """Interface para detectores de placas."""
    
    @abstractmethod
    def detect(self, image: np.ndarray) -> List[PlateRegion]:
        """Detecta regiões de placas na imagem."""
        pass


class ContourPlateDetector(PlateDetector):
    """Detector de placas baseado em contornos."""
    
    def __init__(self, min_confidence: float = 0.7):
        self.min_confidence = min_confidence
    
    def detect(self, image: np.ndarray) -> List[PlateRegion]:
        """
        Detecta placas usando análise de contornos.
        
        Args:
            image: Imagem pré-processada
            
        Returns:
            Lista de regiões de placas detectadas
        """
        try:
            # Binarização
            _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Encontra contornos
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            plate_regions = []
            
            for contour in contours:
                # Filtra por área
                area = cv2.contourArea(contour)
                if area < 500 or area > 50000:  # Filtra áreas muito pequenas ou grandes
                    continue
                
                # Obtém retângulo delimitador
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filtra por proporção (placas geralmente são retangulares)
                aspect_ratio = w / h
                if not (2.0 <= aspect_ratio <= 5.0):  # Proporção típica de placas
                    continue
                
                # Calcula confiança baseada na regularidade do contorno
                confidence = self._calculate_confidence(contour, w, h)
                
                if confidence >= self.min_confidence:
                    plate_regions.append(PlateRegion(x, y, w, h, confidence))
            
            return sorted(plate_regions, key=lambda r: r.confidence, reverse=True)
            
        except Exception as e:
            logger.error("Erro na detecção por contornos: %s", e)
            return []
    
    def _calculate_confidence(self, contour: np.ndarray, width: int, height: int) -> float:
        """Calcula confiança baseada na regularidade do contorno."""
        # Área do contorno vs área do retângulo
        contour_area = cv2.contourArea(contour)
        bbox_area = width * height
        area_ratio = contour_area / bbox_area if bbox_area > 0 else 0
        
        # Solidez do contorno
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        solidity = contour_area / hull_area if hull_area > 0 else 0
        
        # Combina métricas
        confidence = (area_ratio + solidity) / 2
        return min(confidence, 1.0)


class PlateValidator:
    """Validador de placas reconhecidas."""
    
    # Padrões de placas brasileiras
    PLATE_PATTERNS = {
        PlateType.MERCOSUL: re.compile(r'^[A-Z]{3}[0-9][A-Z][0-9]{2}$'),
        PlateType.BRASIL_ANTIGO: re.compile(r'^[A-Z]{3}[0-9]{4}$')
    }
    
    @classmethod
    def validate_plate_format(cls, plate_text: str) -> Optional[PlateType]:
        """
        Valida o formato da placa reconhecida.
        
        Args:
            plate_text: Texto da placa
            
        Returns:
            Tipo da placa se válida, None caso contrário
        """
        # Limpa e padroniza o texto
        cleaned_text = cls._clean_plate_text(plate_text)
        
        for plate_type, pattern in cls.PLATE_PATTERNS.items():
            if pattern.match(cleaned_text):
                return plate_type
        
        return PlateType.UNKNOWN
    
    @staticmethod
    def _clean_plate_text(plate_text: str) -> str:
        """
        Limpa e padroniza o texto da placa.
        
        Args:
            plate_text: Texto bruto da placa
            
        Returns:
            Texto limpo e padronizado
        """
        # Remove espaços, traços e converte para maiúsculas
        cleaned = re.sub(r'[^A-Z0-9]', '', plate_text.upper())
        
        # Corrige possíveis confusões de caracteres
        char_replacements = {
            '0': 'O', '1': 'I', '5': 'S', '8': 'B'
        }
        
        # Aplica substituições apenas se melhorar a validação
        for digit, letter in char_replacements.items():
            temp_text = cleaned.replace(digit, letter)
            if len(temp_text) == 7 and any(p.match(temp_text) for p in PlateValidator.PLATE_PATTERNS.values()):
                cleaned = temp_text
        
        return cleaned
    
    @classmethod
    def calculate_confidence(cls, plate_text: str, original_confidence: float) -> float:
        """
        Calcula confiança final baseada na validação do formato.
        
        Args:
            plate_text: Texto da placa
            original_confidence: Confiança do OCR
            
        Returns:
            Confiança ajustada
        """
        plate_type = cls.validate_plate_format(plate_text)
        
        if plate_type == PlateType.UNKNOWN:
            # Penaliza placas com formato inválido
            return original_confidence * 0.5
        else:
            # Bônus para placas com formato válido
            return min(original_confidence * 1.1, 1.0)


class PlateRecognizer(ABC):
    """Interface para reconhecedores de texto de placas."""
    
    @abstractmethod
    def recognize_text(self, plate_region: np.ndarray) -> Tuple[str, float]:
        """Reconhece texto da placa a partir da região detectada."""
        pass


class TesseractPlateRecognizer(PlateRecognizer):
    """Reconhecedor de placas usando Tesseract OCR."""
    
    def __init__(self):
        try:
            import pytesseract
            self.pytesseract = pytesseract
        except ImportError:
            raise PlateRecognitionError("Tesseract não está instalado")
    
    def recognize_text(self, plate_region: np.ndarray) -> Tuple[str, float]:
        """
        Reconhece texto da placa usando Tesseract.
        
        Args:
            plate_region: Imagem da região da placa
            
        Returns:
            Tupla (texto, confiança)
        """
        try:
            # Configurações otimizadas para placas
            config = '--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            
            # Reconhecimento
            data = self.pytesseract.image_to_data(plate_region, output_type=self.pytesseract.Output.DICT, config=config)
            
            # Filtra resultados com confiança
            confident_texts = []
            confidences = []
            
            for i, text in enumerate(data['text']):
                confidence = data['conf'][i]
                if confidence > 0 and text.strip():
                    confident_texts.append(text.strip())
                    confidences.append(confidence)
            
            if not confident_texts:
                return "", 0.0
            
            # Combina textos e calcula confiança média
            combined_text = ''.join(confident_texts)
            avg_confidence = sum(confidences) / len(confidences) / 100.0  # Normaliza para 0-1
            
            return combined_text, avg_confidence
            
        except Exception as e:
            logger.error("Erro no reconhecimento OCR: %s", e)
            return "", 0.0


class PlateRecognitionUseCase:
    """
    Caso de uso para reconhecimento de placas de veículos.
    
    Orquestra todo o processo:
    - Validação da imagem
    - Pré-processamento
    - Detecção da placa
    - Reconhecimento do texto
    - Validação do resultado
    """
    
    def __init__(
        self,
        plate_detector: PlateDetector,
        plate_recognizer: PlateRecognizer,
        config: Optional[PlateRecognitionConfig] = None
    ):
        self.plate_detector = plate_detector
        self.plate_recognizer = plate_recognizer
        self.config = config or PlateRecognitionConfig()
        self.validator = PlateValidator()
        self.preprocessor = ImagePreprocessor()
    
    def execute(self, image_path: str) -> PlateRecognitionResult:
        """
        Executa o reconhecimento de placa na imagem.
        
        Args:
            image_path: Caminho para a imagem
            
        Returns:
            PlateRecognitionResult: Resultado do reconhecimento
            
        Raises:
            PlateRecognitionError: Em caso de erro no processo
        """
        start_time = datetime.now()
        logger.info("Iniciando reconhecimento de placa: %s", image_path)
        
        try:
            # 1. Validação e pré-processamento
            self.preprocessor.validate_image(image_path)
            processed_image = self.preprocessor.load_and_preprocess(image_path, self.config)
            
            # 2. Detecção da placa
            plate_regions = self.plate_detector.detect(processed_image)
            if not plate_regions:
                raise NoPlateDetectedError("Nenhuma placa detectada na imagem")
            
            # Pega a região com maior confiança
            best_region = plate_regions[0]
            logger.info("Placa detectada: %dx%d @ (%d, %d) - Confiança: %.2f",
                       best_region.width, best_region.height,
                       best_region.x, best_region.y, best_region.confidence)
            
            # 3. Extrai região da placa
            plate_image = self._extract_plate_region(processed_image, best_region)
            
            # 4. Reconhecimento do texto
            plate_text, ocr_confidence = self.plate_recognizer.recognize_text(plate_image)
            if not plate_text:
                raise LowConfidenceError("Não foi possível reconhecer texto na placa")
            
            logger.info("Texto reconhecido: %s (Confiança OCR: %.2f)", plate_text, ocr_confidence)
            
            # 5. Validação e pós-processamento
            final_confidence = self.validator.calculate_confidence(plate_text, ocr_confidence)
            plate_type = self.validator.validate_plate_format(plate_text)
            
            if final_confidence < self.config.min_confidence:
                raise LowConfidenceError(
                    f"Confiança muito baixa: {final_confidence:.2f} "
                    f"(mínimo: {self.config.min_confidence})"
                )
            
            # 6. Calcula tempo de processamento
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = PlateRecognitionResult(
                plate_text=plate_text,
                confidence=final_confidence,
                plate_type=plate_type,
                plate_region=best_region,
                processing_time=processing_time,
                image_path=image_path,
                timestamp=datetime.now(),
                metadata={
                    'image_dimensions': processed_image.shape[:2],
                    'ocr_confidence': ocr_confidence,
                    'detection_confidence': best_region.confidence,
                    'plate_dimensions': (best_region.width, best_region.height),
                    'valid_format': plate_type != PlateType.UNKNOWN
                }
            )
            
            logger.info(
                "Reconhecimento concluído: %s (Tipo: %s, Confiança: %.2f, Tempo: %.2fs)",
                plate_text, plate_type.value, final_confidence, processing_time
            )
            
            return result
            
        except (InvalidImageError, NoPlateDetectedError, LowConfidenceError):
            raise
        except Exception as e:
            logger.error("Erro inesperado no reconhecimento: %s", e)
            raise PlateRecognitionError(f"Erro no reconhecimento: {str(e)}")
    
    def _extract_plate_region(self, image: np.ndarray, region: PlateRegion) -> np.ndarray:
        """
        Extrai a região da placa da imagem.
        
        Args:
            image: Imagem completa
            region: Região da placa
            
        Returns:
            Imagem da placa recortada
        """
        x, y, w, h = region.x, region.y, region.width, region.height
        
        # Adiciona margem para melhor reconhecimento
        margin_x = int(w * 0.1)
        margin_y = int(h * 0.1)
        
        x1 = max(0, x - margin_x)
        y1 = max(0, y - margin_y)
        x2 = min(image.shape[1], x + w + margin_x)
        y2 = min(image.shape[0], y + h + margin_y)
        
        plate_region = image[y1:y2, x1:x2]
        
        # Redimensiona para tamanho padrão se necessário
        if plate_region.shape[0] < 50 or plate_region.shape[1] < 200:
            plate_region = cv2.resize(plate_region, (300, 75))
        
        return plate_region
    
    def batch_process(self, image_paths: List[str]) -> List[PlateRecognitionResult]:
        """
        Processa múltiplas imagens em lote.
        
        Args:
            image_paths: Lista de caminhos de imagens
            
        Returns:
            Lista de resultados
        """
        results = []
        
        for image_path in image_paths:
            try:
                result = self.execute(image_path)
                results.append(result)
            except PlateRecognitionError as e:
                logger.warning("Erro no processamento de %s: %s", image_path, e)
                continue
        
        return results


# Fábrica para criação do use case
class PlateRecognitionFactory:
    """Fábrica para criar instância do use case com dependências."""
    
    @staticmethod
    def create(config: Optional[PlateRecognitionConfig] = None) -> PlateRecognitionUseCase:
        """Cria instância configurada do use case."""
        config = config or PlateRecognitionConfig()
        
        detector = ContourPlateDetector(min_confidence=config.min_confidence)
        recognizer = TesseractPlateRecognizer()
        
        return PlateRecognitionUseCase(
            plate_detector=detector,
            plate_recognizer=recognizer,
            config=config
        )


# Exemplo de uso
if __name__ == "__main__":
    # Configuração básica de logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Cria use case
        config = PlateRecognitionConfig(
            min_confidence=0.7,
            debug_mode=True
        )
        
        use_case = PlateRecognitionFactory.create(config)
        
        # Processa imagem
        result = use_case.execute("exemplo_placa.jpg")
        
        print(f"Placa reconhecida: {result.plate_text}")
        print(f"Confiança: {result.confidence:.2f}")
        print(f"Tipo: {result.plate_type.value}")
        print(f"Tempo de processamento: {result.processing_time:.2f}s")
        print(f"Posição: ({result.plate_region.x}, {result.plate_region.y})")
        
    except PlateRecognitionError as e:
        print(f"Erro no reconhecimento: {e}")
    except Exception as e:
        print(f"Erro inesperado: {e}")