"""OCR Camera view implementation."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QMessageBox, QProgressBar, QComboBox, QCheckBox
)
# Novas importações para Threading:
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRunnable, QObject, QThreadPool 
from PyQt5.QtGui import QImage, QPixmap
import cv2
import numpy as np
from ...core.ocr import process_image, set_ocr_engine, set_preprocessing, detect_text_from_frame
from ...core.face_detection import detect_human_face
import traceback  # Útil para debug de erros na thread
import sys  # Importação necessária para sys.exc_info()
from datetime import datetime, timedelta
from ...data.database.carrier_repository import CarrierRepository

# --- ESTRUTURA DE THREADING ---

class WorkerSignals(QObject):
    """Define signals available from a running worker thread."""
    result = pyqtSignal(object)  # Emite um dict {text, confidence}
    finished = pyqtSignal()      # Emite quando a thread termina
    error = pyqtSignal(tuple)    # Emite informações de erro

class OCRWorker(QRunnable):
    """Runnable para executar a tarefa de OCR em uma thread separada."""
    
    def __init__(self, frame):
        super().__init__()
        # É importante trabalhar com uma cópia do frame para evitar problemas de memória
        self.frame = frame.copy() 
        self.signals = WorkerSignals()

    def run(self):
        """Função a ser executada pela thread (Processamento pesado)."""
        try:
            # Chama a função de processamento pesado
            text, conf = process_image(self.frame)
            raw = None
            if not text:
                try:
                    raw = detect_text_from_frame(self.frame)
                except Exception:
                    raw = None
            self.signals.result.emit({
                'text': text,
                'confidence': float(conf or 0.0),
                'raw_text': raw
            })
        except Exception:
            # Captura e envia o erro de volta para a thread principal
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        finally:
            self.signals.finished.emit()

# --- FIM DA ESTRUTURA DE THREADING ---


class OCRCameraView(QWidget):
    """OCR Camera view for vehicle plate recognition."""
    
    # Signals
    plate_detected = pyqtSignal(str)    # Emitted when a plate is detected
    
    def __init__(self, parent=None):
        """Initialize the OCR camera view."""
        super().__init__(parent)
        self.camera = None
        self.timer = None
        self.last_frame_ts = None
        
        # Variáveis de controle de processamento
        self.threadpool = QThreadPool()
        self.processing = False
        self.frame_count = 0
        self.ocr_rate = 15  # Processa 1 a cada 15 frames (~2x por segundo em 30fps)
        # Face detection cooldown
        self._last_face_alert = None
        self.face_alert_cooldown = 10  # seconds
        
        self.setup_ui()
        self._load_carriers()
        
    # O método setup_ui permanece inalterado
    def setup_ui(self):
        """Setup the camera view interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Camera preview
        self.preview_frame = QLabel()
        self.preview_frame.setMinimumSize(640, 480)
        self.preview_frame.setAlignment(Qt.AlignCenter)
        self.preview_frame.setStyleSheet("""
            QLabel {
                background-color: #212529;
                border-radius: 8px;
                padding: 0; /* Removendo padding para evitar bordas */
            }
        """)
        layout.addWidget(self.preview_frame)
        
        # Controls
        controls = QFrame()
        controls_layout = QHBoxLayout(controls)
        
        # Start/Stop button
        self.toggle_btn = QPushButton("Iniciar Câmera")
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_camera)
        controls_layout.addWidget(self.toggle_btn)

        # OCR Engine selector
        self.engine_select = QComboBox()
        self.engine_select.addItems(["tesseract", "easyocr", "paddle"])
        self.engine_select.setCurrentText("tesseract")
        self.engine_select.currentTextChanged.connect(set_ocr_engine)
        controls_layout.addWidget(QLabel("Engine:"))
        controls_layout.addWidget(self.engine_select)

        # Carrier selector (simple linkage)
        self.carrier_select = QComboBox()
        controls_layout.addWidget(QLabel("Transportadora:"))
        controls_layout.addWidget(self.carrier_select)

        # Preprocessing toggle
        self.preproc_check = QCheckBox("Pré-processamento+")
        self.preproc_check.setChecked(True)
        self.preproc_check.toggled.connect(set_preprocessing)
        controls_layout.addWidget(self.preproc_check)
        
        # Processing indicator
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(200)
        self.progress.hide()
        controls_layout.addWidget(self.progress)
        
        # Status
        self.status_label = QLabel("Câmera desligada")
        self.status_label.setStyleSheet("color: #6c757d;")
        controls_layout.addStretch()
        controls_layout.addWidget(self.status_label)
        
        layout.addWidget(controls)
        
        # Results area
        results = QFrame()
        results.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        results_layout = QVBoxLayout(results)
        
        # Last detection
        self.last_detection = QLabel("Nenhuma placa detectada")
        self.last_detection.setStyleSheet("""
            QLabel {
                font-size: 18px;
                color: #212529;
            }
        """)
        results_layout.addWidget(self.last_detection)
        # Confidence display
        self.confidence_label = QLabel("")
        self.confidence_label.setStyleSheet("color: #6c757d;")
        results_layout.addWidget(self.confidence_label)
        
        layout.addWidget(results)
    
    # Os métodos toggle_camera, start_camera e stop_camera permanecem inalterados
    def toggle_camera(self):
        """Toggle camera on/off."""
        if self.camera is None:
            self.start_camera()
        else:
            self.stop_camera()
            
    def start_camera(self):
        """Start the camera and recognition process."""
        try:
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                # Tenta outras fontes caso a 0 falhe
                self.camera = cv2.VideoCapture(1)
                if not self.camera.isOpened():
                     raise Exception("Não foi possível acessar a câmera (0 ou 1).")
                
            # Setup timer for frame capture
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_frame)
            self.timer.start(30)    # 30ms = ~33fps
            
            # Atualiza UI
            self.toggle_btn.setText("Parar Câmera")
            self.toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            self.status_label.setText("Câmera ativa")
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erro",
                f"Erro ao iniciar câmera: {str(e)}",
                QMessageBox.Ok
            )
            # Garante que a câmera seja parada se houver falha na inicialização
            self.stop_camera() 
            
    def stop_camera(self):
        """Stop the camera and cleanup."""
        if self.timer:
            self.timer.stop()
        if self.camera:
            self.camera.release()
            
        self.camera = None
        self.preview_frame.clear()
        self.toggle_btn.setText("Iniciar Câmera")
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.status_label.setText("Câmera desligada")
        self.processing = False
        self.progress.hide()

    def update_frame(self):
        """Update camera preview and sample frame for OCR."""
        if self.camera is None:
            return
            
        ret, frame = self.camera.read()
        if not ret:
            self.stop_camera()
            return
        self.last_frame_ts = datetime.now()
            
        # Convert frame to RGB for display (CÓDIGO DE VISUALIZAÇÃO)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        
        # CORREÇÃO: Usar bytes_per_line em vez de bytes_per_per_line
        image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.preview_frame.setPixmap(QPixmap.fromImage(image).scaled(
            self.preview_frame.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        ))
        
        # --- LÓGICA DE AMOSTRAGEM E THREADING (NOVA) ---
        if not self.processing:
            self.frame_count += 1
            # Verifica se atingiu a taxa de amostragem definida
            if self.frame_count >= self.ocr_rate: 
                self.process_frame_in_thread(frame)
                self.frame_count = 0 

        # --- Face detection (non-blocking, lightweight) ---
        try:
            detected = detect_human_face(frame)
            if detected:
                now = datetime.now()
                if (self._last_face_alert is None) or ((now - self._last_face_alert).total_seconds() >= self.face_alert_cooldown):
                    self._last_face_alert = now
                    QMessageBox.information(self, "Alerta", "Rosto humano detectado!")
        except Exception:
            pass

    def process_frame_in_thread(self, frame):
        """Inicia o processamento pesado de OCR em uma thread separada."""
        self.processing = True
        self.progress.setRange(0, 0)  # Ativa o indicador de progresso (indeterminado)
        self.progress.show()
        
        worker = OCRWorker(frame)
        worker.signals.result.connect(self.handle_ocr_result)
        worker.signals.error.connect(self.handle_ocr_error)
        worker.signals.finished.connect(self.ocr_processing_done)
        
        self.threadpool.start(worker)

    # --- NOVOS MÉTODOS DE CALLBACK DA THREAD ---

    def handle_ocr_result(self, payload):
        """Recebe o resultado de OCR da thread e atualiza a UI."""
        text = None if not isinstance(payload, dict) else payload.get('text')
        conf = 0.0 if not isinstance(payload, dict) else float(payload.get('confidence') or 0.0)
        raw = None if not isinstance(payload, dict) else payload.get('raw_text')
        if text:
            self.last_detection.setText(f"Placa detectada: {text}")
            self.confidence_label.setText(f"Confiança: {conf*100:.0f}%")
            # Emite apenas o texto para manter compatibilidade com o restante do app
            self.plate_detected.emit(text)
        else:
            if raw:
                self.last_detection.setText(f"Texto bruto detectado: {raw}")
                self.confidence_label.setText("")
            else:
                self.last_detection.setText("Nenhuma placa detectada")
                self.confidence_label.setText("")

    def handle_ocr_error(self, error_info: tuple):
        """Trata erros que ocorreram na thread de processamento."""
        exctype, value, tb_str = error_info
        # Podemos registrar o erro no sistema de logging do projeto aqui.
        self.status_label.setText(f"Erro no OCR: {value}")
        self.last_detection.setText("Erro de Processamento. Tente novamente.")
        
    def ocr_processing_done(self):
        """Executado quando a thread de OCR termina."""
        self.processing = False
        self.progress.hide()
    
    # --- FIM DOS MÉTODOS DE CALLBACK ---
    
    def closeEvent(self, event):
        """Clean up on close."""
        self.stop_camera()
        # É crucial esperar que as threads ativas terminem antes de sair
        self.threadpool.waitForDone() 
        super().closeEvent(event)

    # --- Carrier helpers ---
    def _load_carriers(self):
        """Populate the carrier dropdown from repository."""
        try:
            repo = CarrierRepository()
            rows = repo.get_all()
            self.carrier_select.clear()
            self.carrier_select.addItem("(Nenhuma)", None)
            for r in rows:
                self.carrier_select.addItem(str(r.get('name') or r.get('cnpj') or r.get('id')), r.get('id'))
        except Exception:
            try:
                self.carrier_select.clear()
                self.carrier_select.addItem("(Nenhuma)", None)
            except Exception:
                pass

    def get_selected_carrier_id(self):
        try:
            return self.carrier_select.currentData()
        except Exception:
            return None

    # --- Camera health ---
    def camera_offline_seconds(self):
        try:
            if not self.last_frame_ts:
                return None
            delta = datetime.now() - self.last_frame_ts
            return int(delta.total_seconds())
        except Exception:
            return None