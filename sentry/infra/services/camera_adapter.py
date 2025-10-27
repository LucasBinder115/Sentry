# sentry/infra/services/camera_adapter.py

import logging
import time
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import cv2
import numpy as np

# Configuração de logging
logger = logging.getLogger(__name__)


# Exceções customizadas
class CameraError(Exception):
    """Exceção base para erros de câmera."""
    pass


class CameraConnectionError(CameraError):
    """Exceção para falhas de conexão com a câmera."""
    pass


class CameraCaptureError(CameraError):
    """Exceção para falhas na captura de imagens."""
    pass


class CameraConfigurationError(CameraError):
    """Exceção para erros de configuração da câmera."""
    pass


class CameraMode(Enum):
    """Modos de operação da câmera."""
    SINGLE_SHOT = "single_shot"
    CONTINUOUS = "continuous"
    MOTION_DETECTION = "motion_detection"


@dataclass
class CameraConfig:
    """Configuração da câmera."""
    camera_index: int = 0
    resolution: Tuple[int, int] = (1920, 1080)
    fps: int = 30
    brightness: int = 50
    contrast: int = 50
    saturation: int = 50
    exposure: int = -1  # Auto-exposure
    focus: int = 0  # Auto-focus
    codec: str = "MJPG"
    buffer_size: int = 10
    timeout_ms: int = 5000


@dataclass
class CaptureResult:
    """Resultado da captura de imagem."""
    success: bool
    frame: Optional[np.ndarray]
    timestamp: datetime
    metadata: Dict[str, Any]
    file_path: Optional[Path] = None


class CameraAdapter:
    """
    Adaptador robusto para captura de imagens da câmera.
    
    Suporta múltiplos modos de operação e fornece tratamento
    completo de erros e métricas de performance.
    """
    
    def __init__(self, config: Optional[CameraConfig] = None):
        self.config = config or CameraConfig()
        self._camera = None
        self._is_connected = False
        self._capture_count = 0
        self._error_count = 0
        self._last_capture_time = None
        
        # Estatísticas
        self.stats = {
            'total_captures': 0,
            'successful_captures': 0,
            'failed_captures': 0,
            'total_connection_time': 0.0,
            'last_connection_time': None
        }
        
        self._initialize_camera()
    
    def _initialize_camera(self):
        """Inicializa a conexão com a câmera."""
        logger.info("Inicializando câmera (índice: %d)", self.config.camera_index)
        
        try:
            # Tenta conectar com a câmera
            self._camera = cv2.VideoCapture(self.config.camera_index)
            
            if not self._camera.isOpened():
                raise CameraConnectionError(
                    f"Não foi possível conectar com a câmera no índice {self.config.camera_index}"
                )
            
            # Aplica configurações
            self._apply_camera_settings()
            
            # Testa a captura
            test_success = self._test_camera()
            
            if test_success:
                self._is_connected = True
                logger.info("Câmera inicializada com sucesso")
            else:
                raise CameraConnectionError("Teste de captura da câmera falhou")
                
        except Exception as e:
            self._cleanup()
            if isinstance(e, CameraConnectionError):
                raise
            else:
                raise CameraConnectionError(f"Erro na inicialização da câmera: {str(e)}") from e
    
    def _apply_camera_settings(self):
        """Aplica as configurações da câmera."""
        try:
            # Configura resolução
            self._camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.resolution[0])
            self._camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.resolution[1])
            
            # Configura FPS
            self._camera.set(cv2.CAP_PROP_FPS, self.config.fps)
            
            # Configura propriedades da imagem
            self._camera.set(cv2.CAP_PROP_BRIGHTNESS, self.config.brightness / 100.0)
            self._camera.set(cv2.CAP_PROP_CONTRAST, self.config.contrast / 100.0)
            self._camera.set(cv2.CAP_PROP_SATURATION, self.config.saturation / 100.0)
            
            # Configura exposição e foco
            if self.config.exposure >= 0:
                self._camera.set(cv2.CAP_PROP_EXPOSURE, self.config.exposure)
            
            if self.config.focus >= 0:
                self._camera.set(cv2.CAP_PROP_FOCUS, self.config.focus)
            
            # Configura codec
            fourcc = cv2.VideoWriter_fourcc(*self.config.codec)
            self._camera.set(cv2.CAP_PROP_FOURCC, fourcc)
            
            # Configura buffer
            self._camera.set(cv2.CAP_PROP_BUFFERSIZE, self.config.buffer_size)
            
            logger.debug("Configurações da câmera aplicadas com sucesso")
            
        except Exception as e:
            raise CameraConfigurationError(f"Erro ao aplicar configurações: {str(e)}") from e
    
    def _test_camera(self) -> bool:
        """Executa teste de captura para verificar funcionamento."""
        try:
            start_time = time.time()
            success, frame = self._camera.read()
            capture_time = time.time() - start_time
            
            if success and frame is not None:
                logger.info(
                    "Teste de câmera bem-sucedido. Resolução: %dx%d, Tempo: %.3fs",
                    frame.shape[1], frame.shape[0], capture_time
                )
                return True
            else:
                logger.warning("Teste de câmera falhou - frame vazio ou captura mal-sucedida")
                return False
                
        except Exception as e:
            logger.error("Erro durante teste da câmera: %s", e)
            return False
    
    def capture_frame(self) -> CaptureResult:
        """
        Captura um único frame da câmera.
        
        Returns:
            CaptureResult: Resultado da captura com metadados
            
        Raises:
            CameraCaptureError: Se a captura falhar
        """
        logger.debug("Iniciando captura de frame")
        
        if not self._is_connected or self._camera is None:
            raise CameraConnectionError("Câmera não está conectada")
        
        start_time = time.time()
        timestamp = datetime.now()
        
        try:
            # Captura frame com timeout
            self._camera.set(cv2.CAP_PROP_POS_MSEC, 0)
            success, frame = self._camera.read()
            capture_time = time.time() - start_time
            
            self.stats['total_captures'] += 1
            self._last_capture_time = timestamp
            
            if success and frame is not None:
                self.stats['successful_captures'] += 1
                
                # Valida qualidade da imagem
                quality_ok = self._validate_image_quality(frame)
                
                metadata = {
                    'capture_time_seconds': capture_time,
                    'resolution': (frame.shape[1], frame.shape[0]),
                    'channels': frame.shape[2] if len(frame.shape) > 2 else 1,
                    'quality_check_passed': quality_ok,
                    'brightness_mean': float(np.mean(frame)),
                    'capture_count': self.stats['total_captures']
                }
                
                logger.debug(
                    "Frame capturado com sucesso: %dx%d, tempo: %.3fs, qualidade: %s",
                    frame.shape[1], frame.shape[0], capture_time, 
                    "OK" if quality_ok else "BAIXA"
                )
                
                return CaptureResult(
                    success=True,
                    frame=frame,
                    timestamp=timestamp,
                    metadata=metadata
                )
            else:
                self.stats['failed_captures'] += 1
                self._error_count += 1
                
                logger.warning("Falha na captura do frame (tentativa %d)", self._error_count)
                
                # Tenta reconectar após múltiplas falhas
                if self._error_count >= 3:
                    self._reconnect_camera()
                
                return CaptureResult(
                    success=False,
                    frame=None,
                    timestamp=timestamp,
                    metadata={
                        'capture_time_seconds': capture_time,
                        'error_count': self._error_count,
                        'reason': 'capture_failed'
                    }
                )
                
        except Exception as e:
            self.stats['failed_captures'] += 1
            self._error_count += 1
            logger.error("Erro durante captura do frame: %s", e)
            
            raise CameraCaptureError(f"Erro na captura: {str(e)}") from e
    
    def _validate_image_quality(self, frame: np.ndarray) -> bool:
        """
        Valida a qualidade básica da imagem capturada.
        
        Args:
            frame: Frame capturado
            
        Returns:
            True se a qualidade for aceitável
        """
        try:
            # Verifica se a imagem não está muito escura
            brightness = np.mean(frame)
            if brightness < 30:  # Muito escuro
                logger.warning("Imagem muito escura: brilho médio = %.2f", brightness)
                return False
            
            # Verifica se a imagem não está muito clara (saturada)
            if brightness > 220:  # Muito claro
                logger.warning("Imagem muito clara: brilho médio = %.2f", brightness)
                return False
            
            # Verifica contraste (desvio padrão dos pixels)
            contrast = np.std(frame)
            if contrast < 10:  # Contraste muito baixo
                logger.warning("Contraste muito baixo: %.2f", contrast)
                return False
            
            return True
            
        except Exception as e:
            logger.warning("Erro na validação de qualidade: %s", e)
            return True  # Assume OK em caso de erro na validação
    
    def capture_and_save(self, file_path: Path, quality: int = 95) -> CaptureResult:
        """
        Captura um frame e salva diretamente em arquivo.
        
        Args:
            file_path: Caminho onde salvar a imagem
            quality: Qualidade da imagem (0-100)
            
        Returns:
            CaptureResult: Resultado da operação
        """
        logger.info("Capturando e salvando imagem: %s", file_path)
        
        # Garante que o diretório existe
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        capture_result = self.capture_frame()
        
        if capture_result.success and capture_result.frame is not None:
            try:
                # Converte para RGB se necessário (OpenCV usa BGR)
                if len(capture_result.frame.shape) == 3 and capture_result.frame.shape[2] == 3:
                    frame_rgb = cv2.cvtColor(capture_result.frame, cv2.COLOR_BGR2RGB)
                else:
                    frame_rgb = capture_result.frame
                
                # Salva a imagem
                success = cv2.imwrite(
                    str(file_path), 
                    frame_rgb,
                    [cv2.IMWRITE_JPEG_QUALITY, quality]
                )
                
                if success:
                    capture_result.file_path = file_path
                    capture_result.metadata['saved_path'] = str(file_path)
                    capture_result.metadata['file_size'] = file_path.stat().st_size if file_path.exists() else 0
                    logger.info("Imagem salva com sucesso: %s", file_path)
                else:
                    logger.error("Falha ao salvar imagem: %s", file_path)
                    capture_result.success = False
                    
            except Exception as e:
                logger.error("Erro ao salvar imagem %s: %s", file_path, e)
                capture_result.success = False
        
        return capture_result
    
    def capture_continuous(self, duration: float, callback, interval: float = 1.0):
        """
        Captura frames continuamente por um período.
        
        Args:
            duration: Duração total em segundos
            callback: Função chamada para cada frame capturado
            interval: Intervalo entre capturas em segundos
        """
        logger.info("Iniciando captura contínua por %.1f segundos", duration)
        
        start_time = time.time()
        frame_count = 0
        
        try:
            while (time.time() - start_time) < duration:
                frame_start = time.time()
                
                result = self.capture_frame()
                if result.success:
                    frame_count += 1
                    callback(result)
                
                # Calcula tempo de espera para manter o intervalo
                processing_time = time.time() - frame_start
                wait_time = max(0, interval - processing_time)
                
                if wait_time > 0:
                    time.sleep(wait_time)
            
            logger.info("Captura contínua concluída: %d frames capturados", frame_count)
            
        except Exception as e:
            logger.error("Erro durante captura contínua: %s", e)
            raise
    
    def _reconnect_camera(self):
        """Tenta reconectar a câmera após falhas."""
        logger.warning("Tentando reconectar câmera após %d falhas", self._error_count)
        
        self._cleanup()
        time.sleep(2)  # Aguarda antes de reconectar
        
        try:
            self._initialize_camera()
            self._error_count = 0
            logger.info("Reconexão com câmera bem-sucedida")
        except Exception as e:
            logger.error("Falha na reconexão com câmera: %s", e)
            raise CameraConnectionError("Não foi possível reconectar com a câmera") from e
    
    def _cleanup(self):
        """Libera recursos da câmera."""
        if self._camera is not None:
            try:
                self._camera.release()
                logger.debug("Recursos da câmera liberados")
            except Exception as e:
                logger.warning("Erro ao liberar recursos da câmera: %s", e)
            finally:
                self._camera = None
                self._is_connected = False
    
    def get_camera_info(self) -> Dict[str, Any]:
        """Retorna informações sobre a câmera e seu status."""
        if not self._is_connected or self._camera is None:
            return {
                'connected': False,
                'status': 'disconnected',
                'camera_index': self.config.camera_index
            }
        
        try:
            # Obtém propriedades da câmera
            width = int(self._camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self._camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self._camera.get(cv2.CAP_PROP_FPS)
            brightness = self._camera.get(cv2.CAP_PROP_BRIGHTNESS) * 100
            
            return {
                'connected': True,
                'status': 'operational',
                'camera_index': self.config.camera_index,
                'resolution': (width, height),
                'fps': fps,
                'brightness': brightness,
                'capture_stats': self.stats.copy(),
                'last_capture': self._last_capture_time,
                'error_count': self._error_count
            }
        except Exception as e:
            logger.warning("Erro ao obter informações da câmera: %s", e)
            return {
                'connected': False,
                'status': 'error',
                'camera_index': self.config.camera_index,
                'error': str(e)
            }
    
    def __enter__(self):
        """Suporte para context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Garante que os recursos sejam liberados."""
        self._cleanup()


# Fábrica para criação de adaptadores de câmera
class CameraAdapterFactory:
    """Fábrica para criar instâncias de CameraAdapter."""
    
    @staticmethod
    def create_default_adapter(camera_index: int = 0) -> CameraAdapter:
        """Cria um adaptador com configurações padrão."""
        config = CameraConfig(camera_index=camera_index)
        return CameraAdapter(config)
    
    @staticmethod
    def create_high_quality_adapter(camera_index: int = 0) -> CameraAdapter:
        """Cria um adaptador otimizado para alta qualidade."""
        config = CameraConfig(
            camera_index=camera_index,
            resolution=(3840, 2160),  # 4K
            fps=15,
            brightness=60,
            contrast=60
        )
        return CameraAdapter(config)
    
    @staticmethod
    def create_fast_adapter(camera_index: int = 0) -> CameraAdapter:
        """Cria um adaptador otimizado para velocidade."""
        config = CameraConfig(
            camera_index=camera_index,
            resolution=(1280, 720),  # HD
            fps=60,
            buffer_size=5
        )
        return CameraAdapter(config)


# Exemplo de uso
if __name__ == "__main__":
    # Configuração básica de logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Cria adaptador de câmera
        camera = CameraAdapterFactory.create_default_adapter()
        
        # Obtém informações da câmera
        info = camera.get_camera_info()
        print("=== Informações da Câmera ===")
        for key, value in info.items():
            print(f"{key}: {value}")
        
        # Captura e salva uma imagem
        if info['connected']:
            output_path = Path("test_capture.jpg")
            result = camera.capture_and_save(output_path)
            
            if result.success:
                print(f"\n✅ Imagem salva: {output_path}")
                print(f"Resolução: {result.metadata['resolution']}")
                print(f"Tempo de captura: {result.metadata['capture_time_seconds']:.3f}s")
            else:
                print("\n❌ Falha na captura da imagem")
        
        # Limpa recursos
        camera._cleanup()
        
    except CameraError as e:
        print(f"❌ Erro de câmera: {e}")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")