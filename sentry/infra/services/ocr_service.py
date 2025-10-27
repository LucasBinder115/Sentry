# sentry/infra/services/ocr_service.py

import logging
import cv2
import numpy as np
from typing import Optional, Tuple, Dict, Any, List
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import easyocr
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter

# Configuração de logging
logger = logging.getLogger(__name__)


# Exceções customizadas
class OcrError(Exception):
    """Exceção base para erros de OCR."""
    pass


class ImageProcessingError(OcrError):
    """Exceção para erros no processamento de imagem."""
    pass


class PlateDetectionError(OcrError):
    """Exceção para falhas na detecção de placas."""
    pass


class OcrInitializationError(OcrError):
    """Exceção para erros na inicialização do OCR."""
    pass


class OcrEngine(Enum):
    """Motores de OCR suportados."""
    EASYOCR = "easyocr"
    TESSERACT = "tesseract"
    HYBRID = "hybrid"  # Combina ambos para melhor precisão


@dataclass
class OcrConfig:
    """Configuração do serviço OCR."""
    engine: OcrEngine = OcrEngine.HYBRID
    languages: List[str] = None
    gpu: bool = False
    contrast_enhance: bool = True
    sharpness_enhance: bool = True
    denoise: bool = True
    confidence_threshold: float = 0.7
    plate_validation: bool = True
    preprocess_image: bool = True


@dataclass
class PlateRecognitionResult:
    """Resultado do reconhecimento de placa."""
    plate_text: str
    confidence: float
    engine_used: OcrEngine
    processing_time: float
    image_path: Path
    timestamp: datetime
    bounding_box: Optional[Tuple[int, int, int, int]] = None
    metadata: Dict[str, Any] = None


class ImagePreprocessor:
    """Pré-processador de imagens para otimizar OCR."""
    
    @staticmethod
    def load_image(image_path: Path) -> np.ndarray:
        """
        Carrega imagem com tratamento de erro.
        
        Args:
            image_path: Caminho da imagem
            
        Returns:
            Imagem como array numpy
            
        Raises:
            ImageProcessingError: Se a imagem não puder ser carregada
        """
        try:
            if not image_path.exists():
                raise ImageProcessingError(f"Arquivo não encontrado: {image_path}")
            
            image = cv2.imread(str(image_path))
            if image is None:
                raise ImageProcessingError(f"Não foi possível carregar imagem: {image_path}")
            
            logger.debug("Imagem carregada: %s (%dx%d)", image_path, image.shape[1], image.shape[0])
            return image
            
        except Exception as e:
            raise ImageProcessingError(f"Erro ao carregar imagem {image_path}: {str(e)}") from e
    
    @staticmethod
    def preprocess_image(image: np.ndarray, config: OcrConfig) -> np.ndarray:
        """
        Aplica pré-processamento para melhorar OCR.
        
        Args:
            image: Imagem original
            config: Configuração de pré-processamento
            
        Returns:
            Imagem pré-processada
        """
        try:
            processed = image.copy()
            
            # Converte para escala de cinza
            if len(processed.shape) == 3:
                processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
            
            # Aplica filtro de mediana para redução de ruído
            if config.denoise:
                processed = cv2.medianBlur(processed, 3)
            
            # Melhora contraste usando CLAHE
            if config.contrast_enhance:
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                processed = clahe.apply(processed)
            
            # Aplica sharpening
            if config.sharpness_enhance:
                kernel = np.array([[-1, -1, -1],
                                 [-1, 9, -1],
                                 [-1, -1, -1]])
                processed = cv2.filter2D(processed, -1, kernel)
            
            # Binarização adaptativa
            processed = cv2.adaptiveThreshold(
                processed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            logger.debug("Pré-processamento de imagem aplicado")
            return processed
            
        except Exception as e:
            logger.warning("Erro no pré-processamento: %s. Usando imagem original.", e)
            return image
    
    @staticmethod
    def extract_plate_region(image: np.ndarray) -> Optional[np.ndarray]:
        """
        Tenta extrair região da placa usando detecção de contornos.
        
        Args:
            image: Imagem completa
            
        Returns:
            Região da placa ou None se não detectada
        """
        try:
            # Converte para escala de cinza se necessário
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Aplica filtro bilateral para preservar bordas
            filtered = cv2.bilateralFilter(gray, 11, 17, 17)
            
            # Detecta bordas
            edged = cv2.Canny(filtered, 30, 200)
            
            # Encontra contornos
            contours, _ = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
            
            plate_contour = None
            
            # Procura por contorno retangular (placa)
            for contour in contours:
                # Aproxima contorno
                epsilon = 0.018 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # Placas geralmente são retangulares (4 vértices)
                if len(approx) == 4:
                    plate_contour = approx
                    break
            
            if plate_contour is not None:
                # Extrai região da placa
                x, y, w, h = cv2.boundingRect(plate_contour)
                
                # Adiciona margem
                margin_x = int(w * 0.1)
                margin_y = int(h * 0.1)
                x = max(0, x - margin_x)
                y = max(0, y - margin_y)
                w = min(image.shape[1] - x, w + 2 * margin_x)
                h = min(image.shape[0] - y, h + 2 * margin_y)
                
                plate_region = image[y:y+h, x:x+w]
                logger.debug("Região da placa detectada: %dx%d", w, h)
                return plate_region
            
            logger.debug("Nenhuma região de placa detectada")
            return None
            
        except Exception as e:
            logger.warning("Erro na detecção de região da placa: %s", e)
            return None


class PlateValidator:
    """Validador de placas reconhecidas."""
    
    # Padrões de placas brasileiras
    PLATE_PATTERNS = {
        'mercosul': r'^[A-Z]{3}[0-9][A-Z][0-9]{2}$',
        'old_format': r'^[A-Z]{3}[0-9]{4}$'
    }
    
    @staticmethod
    def validate_plate_format(plate_text: str) -> Tuple[bool, str]:
        """
        Valida formato da placa.
        
        Args:
            plate_text: Texto da placa reconhecida
            
        Returns:
            Tuple (é_válida, formato_detectado)
        """
        import re
        
        cleaned_plate = PlateValidator.clean_plate_text(plate_text)
        
        for format_name, pattern in PlateValidator.PLATE_PATTERNS.items():
            if re.match(pattern, cleaned_plate):
                return True, format_name
        
        return False, "invalid"
    
    @staticmethod
    def clean_plate_text(plate_text: str) -> str:
        """
        Limpa e padroniza texto da placa.
        
        Args:
            plate_text: Texto bruto da placa
            
        Returns:
            Texto limpo da placa
        """
        import re
        
        # Remove caracteres especiais e converte para maiúsculas
        cleaned = re.sub(r'[^A-Z0-9]', '', plate_text.upper())
        
        # Corrige confusões comuns de caracteres
        char_replacements = {
            '0': 'O', '1': 'I', '5': 'S', '8': 'B'
        }
        
        # Aplica substituições se melhorar a validação
        for digit, letter in char_replacements.items():
            temp_plate = cleaned.replace(digit, letter)
            if len(temp_plate) == 7:  # Tamanho padrão de placas
                for pattern in PlateValidator.PLATE_PATTERNS.values():
                    if re.match(pattern, temp_plate):
                        return temp_plate
        
        return cleaned
    
    @staticmethod
    def calculate_confidence(original_confidence: float, plate_text: str) -> float:
        """
        Calcula confiança final baseada na validação.
        
        Args:
            original_confidence: Confiança do OCR
            plate_text: Texto da placa
            
        Returns:
            Confiança ajustada
        """
        is_valid, _ = PlateValidator.validate_plate_format(plate_text)
        
        if is_valid:
            # Bônus para placas com formato válido
            return min(original_confidence * 1.2, 1.0)
        else:
            # Penalidade para placas com formato inválido
            return original_confidence * 0.6


class OcrService:
    """
    Serviço robusto para Reconhecimento Óptico de Caracteres (OCR)
    com suporte a múltiplos motores e validação de placas.
    """
    
    def __init__(self, config: Optional[OcrConfig] = None):
        self.config = config or OcrConfig()
        self.languages = self.config.languages or ['en', 'pt']
        
        # Inicializa motores
        self.easyocr_reader = None
        self.tesseract_initialized = False
        
        self._initialize_engines()
        self.image_preprocessor = ImagePreprocessor()
        self.plate_validator = PlateValidator()
        
        logger.info("OCR Service inicializado com motor: %s", self.config.engine.value)
    
    def _initialize_engines(self):
        """Inicializa os motores de OCR configurados."""
        try:
            # Inicializa EasyOCR se necessário
            if self.config.engine in [OcrEngine.EASYOCR, OcrEngine.HYBRID]:
                self.easyocr_reader = easyocr.Reader(
                    self.languages,
                    gpu=self.config.gpu,
                    download_enabled=True
                )
                logger.info("EasyOCR inicializado (GPU: %s)", self.config.gpu)
            
            # Verifica Tesseract se necessário
            if self.config.engine in [OcrEngine.TESSERACT, OcrEngine.HYBRID]:
                try:
                    pytesseract.get_tesseract_version()
                    self.tesseract_initialized = True
                    logger.info("Tesseract inicializado")
                except Exception as e:
                    logger.warning("Tesseract não disponível: %s", e)
                    if self.config.engine == OcrEngine.TESSERACT:
                        raise OcrInitializationError("Tesseract não está disponível") from e
            
        except Exception as e:
            raise OcrInitializationError(f"Erro na inicialização do OCR: {str(e)}") from e
    
    def read_plate_from_image(self, image_path: str) -> PlateRecognitionResult:
        """
        Processa uma imagem e retorna o texto da placa reconhecido.
        
        Args:
            image_path: Caminho para a imagem
            
        Returns:
            PlateRecognitionResult: Resultado do reconhecimento
            
        Raises:
            ImageProcessingError: Se a imagem não puder ser processada
            PlateDetectionError: Se a placa não puder ser reconhecida
            OcrError: Para outros erros de OCR
        """
        start_time = datetime.now()
        image_path = Path(image_path)
        
        logger.info("Processando imagem para OCR: %s", image_path)
        
        try:
            # Carrega e pré-processa imagem
            original_image = self.image_preprocessor.load_image(image_path)
            
            if self.config.preprocess_image:
                processed_image = self.image_preprocessor.preprocess_image(original_image, self.config)
            else:
                processed_image = original_image
            
            # Tenta extrair região da placa
            plate_region = self.image_preprocessor.extract_plate_region(original_image)
            ocr_image = plate_region if plate_region is not None else processed_image
            
            # Executa OCR baseado no motor configurado
            if self.config.engine == OcrEngine.EASYOCR:
                plate_text, confidence = self._recognize_with_easyocr(ocr_image)
            elif self.config.engine == OcrEngine.TESSERACT:
                plate_text, confidence = self._recognize_with_tesseract(ocr_image)
            elif self.config.engine == OcrEngine.HYBRID:
                plate_text, confidence = self._recognize_with_hybrid(ocr_image)
            else:
                raise OcrError(f"Motor OCR não suportado: {self.config.engine}")
            
            # Valida e ajusta confiança
            if self.config.plate_validation:
                confidence = self.plate_validator.calculate_confidence(confidence, plate_text)
            
            # Verifica se atinge threshold de confiança
            if confidence < self.config.confidence_threshold:
                logger.warning(
                    "Confiança abaixo do threshold: %.2f < %.2f", 
                    confidence, self.config.confidence_threshold
                )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = PlateRecognitionResult(
                plate_text=plate_text,
                confidence=confidence,
                engine_used=self.config.engine,
                processing_time=processing_time,
                image_path=image_path,
                timestamp=datetime.now(),
                metadata={
                    'plate_region_extracted': plate_region is not None,
                    'image_dimensions': original_image.shape[:2],
                    'confidence_threshold': self.config.confidence_threshold
                }
            )
            
            logger.info(
                "Placa reconhecida: '%s' (confiança: %.2f, tempo: %.2fs)",
                plate_text, confidence, processing_time
            )
            
            return result
            
        except (ImageProcessingError, PlateDetectionError, OcrError):
            raise
        except Exception as e:
            logger.error("Erro inesperado no OCR: %s", e)
            raise OcrError(f"Erro no processamento OCR: {str(e)}") from e
    
    def _recognize_with_easyocr(self, image: np.ndarray) -> Tuple[str, float]:
        """
        Reconhece placa usando EasyOCR.
        
        Args:
            image: Imagem para processar
            
        Returns:
            Tuple (texto, confiança)
        """
        try:
            # Converte BGR para RGB se necessário
            if len(image.shape) == 3:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            
            results = self.easyocr_reader.readtext(image_rgb)
            
            if not results:
                raise PlateDetectionError("Nenhum texto detectado pelo EasyOCR")
            
            # Filtra resultados por confiança e tamanho
            valid_results = []
            for (bbox, text, confidence) in results:
                cleaned_text = self.plate_validator.clean_plate_text(text)
                if 3 <= len(cleaned_text) <= 8:  # Tamanho razoável para placas
                    valid_results.append((cleaned_text, confidence))
            
            if not valid_results:
                raise PlateDetectionError("Nenhum texto com formato de placa detectado")
            
            # Ordena por confiança e pega o melhor resultado
            valid_results.sort(key=lambda x: x[1], reverse=True)
            best_text, best_confidence = valid_results[0]
            
            return best_text, best_confidence
            
        except Exception as e:
            logger.error("Erro no EasyOCR: %s", e)
            raise PlateDetectionError(f"Falha no EasyOCR: {str(e)}") from e
    
    def _recognize_with_tesseract(self, image: np.ndarray) -> Tuple[str, float]:
        """
        Reconhece placa usando Tesseract.
        
        Args:
            image: Imagem para processar
            
        Returns:
            Tuple (texto, confiança)
        """
        if not self.tesseract_initialized:
            raise OcrError("Tesseract não está inicializado")
        
        try:
            # Configurações otimizadas para placas
            config = '--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            
            # Converte para PIL Image
            if len(image.shape) == 3:
                pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            else:
                pil_image = Image.fromarray(image)
            
            # Aplica melhorias na imagem
            enhancer = ImageEnhance.Contrast(pil_image)
            pil_image = enhancer.enhance(2.0)
            
            enhancer = ImageEnhance.Sharpness(pil_image)
            pil_image = enhancer.enhance(2.0)
            
            # Executa OCR
            data = pytesseract.image_to_data(pil_image, output_type=pytesseract.Output.DICT, config=config)
            
            # Processa resultados
            valid_texts = []
            for i, text in enumerate(data['text']):
                confidence = float(data['conf'][i]) / 100.0  # Normaliza para 0-1
                cleaned_text = self.plate_validator.clean_plate_text(text)
                
                if (cleaned_text and confidence > 0.1 and 
                    3 <= len(cleaned_text) <= 8):
                    valid_texts.append((cleaned_text, confidence))
            
            if not valid_texts:
                raise PlateDetectionError("Nenhum texto válido detectado pelo Tesseract")
            
            # Ordena por confiança
            valid_texts.sort(key=lambda x: x[1], reverse=True)
            best_text, best_confidence = valid_texts[0]
            
            return best_text, best_confidence
            
        except Exception as e:
            logger.error("Erro no Tesseract: %s", e)
            raise PlateDetectionError(f"Falha no Tesseract: {str(e)}") from e
    
    def _recognize_with_hybrid(self, image: np.ndarray) -> Tuple[str, float]:
        """
        Reconhece placa usando ambos os motores e combina resultados.
        
        Args:
            image: Imagem para processar
            
        Returns:
            Tuple (texto, confiança)
        """
        results = []
        
        # Tenta EasyOCR
        if self.easyocr_reader:
            try:
                easyocr_text, easyocr_confidence = self._recognize_with_easyocr(image)
                results.append(('easyocr', easyocr_text, easyocr_confidence))
            except Exception as e:
                logger.warning("EasyOCR falhou: %s", e)
        
        # Tenta Tesseract
        if self.tesseract_initialized:
            try:
                tesseract_text, tesseract_confidence = self._recognize_with_tesseract(image)
                results.append(('tesseract', tesseract_text, tesseract_confidence))
            except Exception as e:
                logger.warning("Tesseract falhou: %s", e)
        
        if not results:
            raise PlateDetectionError("Ambos os motores OCR falharam")
        
        # Escolhe o melhor resultado baseado na confiança
        results.sort(key=lambda x: x[2], reverse=True)
        best_engine, best_text, best_confidence = results[0]
        
        logger.debug("Motor híbrido escolheu: %s (confiança: %.2f)", best_engine, best_confidence)
        return best_text, best_confidence
    
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
                result = self.read_plate_from_image(image_path)
                results.append(result)
            except OcrError as e:
                logger.warning("Falha no processamento de %s: %s", image_path, e)
                # Continua com as próximas imagens
        
        logger.info("Processamento em lote concluído: %d sucessos, %d falhas", 
                   len(results), len(image_paths) - len(results))
        
        return results


# Fábrica para criação de serviços OCR
class OcrServiceFactory:
    """Fábrica para criar instâncias de OcrService com configurações comuns."""
    
    @staticmethod
    def create_default_service() -> OcrService:
        """Cria serviço com configuração padrão (híbrida)."""
        config = OcrConfig(engine=OcrEngine.HYBRID)
        return OcrService(config)
    
    @staticmethod
    def create_high_accuracy_service() -> OcrService:
        """Cria serviço otimizado para alta precisão."""
        config = OcrConfig(
            engine=OcrEngine.HYBRID,
            contrast_enhance=True,
            sharpness_enhance=True,
            confidence_threshold=0.8,
            preprocess_image=True
        )
        return OcrService(config)
    
    @staticmethod
    def create_fast_service() -> OcrService:
        """Cria serviço otimizado para velocidade."""
        config = OcrConfig(
            engine=OcrEngine.EASYOCR,
            preprocess_image=False,
            confidence_threshold=0.6
        )
        return OcrService(config)
    
    @staticmethod
    def create_gpu_service() -> OcrService:
        """Cria serviço otimizado para GPU."""
        config = OcrConfig(
            engine=OcrEngine.EASYOCR,
            gpu=True,
            preprocess_image=True
        )
        return OcrService(config)


# Exemplo de uso
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Cria serviço OCR
        ocr_service = OcrServiceFactory.create_default_service()
        
        # Testa com uma imagem (substitua pelo caminho real)
        test_image = "data/test_plate.jpg"
        
        if Path(test_image).exists():
            result = ocr_service.read_plate_from_image(test_image)
            
            print("=== Resultado do OCR ===")
            print(f"Placa: {result.plate_text}")
            print(f"Confiança: {result.confidence:.2f}")
            print(f"Motor: {result.engine_used.value}")
            print(f"Tempo: {result.processing_time:.2f}s")
            print(f"Válida: {PlateValidator.validate_plate_format(result.plate_text)[0]}")
        else:
            print("⚠️  Imagem de teste não encontrada. Criando imagem simulada...")
            
            # Cria uma imagem simulada para teste
            test_image = "data/test_plate_simulated.jpg"
            Path("data").mkdir(exist_ok=True)
            
            # Cria imagem com texto simulado
            img = np.ones((100, 300, 3), dtype=np.uint8) * 255
            cv2.putText(img, "ABC1D23", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
            cv2.imwrite(test_image, img)
            
            result = ocr_service.read_plate_from_image(test_image)
            print(f"✅ Placa reconhecida na imagem simulada: {result.plate_text}")
        
    except OcrError as e:
        print(f"❌ Erro de OCR: {e}")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")