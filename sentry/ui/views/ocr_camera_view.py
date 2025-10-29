"""OCR Camera view implementation."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QMessageBox, QProgressBar
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
import cv2
import numpy as np
from ...core.ocr import process_image

class OCRCameraView(QWidget):
    """OCR Camera view for vehicle plate recognition."""
    
    # Signals
    plate_detected = pyqtSignal(str)  # Emitted when a plate is detected
    
    def __init__(self, parent=None):
        """Initialize the OCR camera view."""
        super().__init__(parent)
        self.camera = None
        self.timer = None
        self.processing = False
        self.setup_ui()
        
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
        
        layout.addWidget(results)
        
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
                raise Exception("Não foi possível acessar a câmera")
                
            # Setup timer for frame capture
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_frame)
            self.timer.start(30)  # 30ms = ~33fps
            
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
        
    def update_frame(self):
        """Update camera preview and process frame for OCR."""
        if self.camera is None:
            return
            
        ret, frame = self.camera.read()
        if not ret:
            self.stop_camera()
            return
            
        # Convert frame to RGB for display
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        
        # Convert to QImage and display
        image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.preview_frame.setPixmap(QPixmap.fromImage(image).scaled(
            self.preview_frame.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        ))
        
        # Process frame for OCR if not already processing
        if not self.processing:
            self.process_frame(frame)
            
    def process_frame(self, frame):
        """Process frame for OCR in a non-blocking way."""
        self.processing = True
        self.progress.setRange(0, 0)
        self.progress.show()
        
        try:
            # Process image using OCR
            plate_text = process_image(frame)
            
            if plate_text:
                self.last_detection.setText(f"Placa detectada: {plate_text}")
                self.plate_detected.emit(plate_text)
                
        except Exception as e:
            self.status_label.setText(f"Erro: {str(e)}")
            
        finally:
            self.processing = False
            self.progress.hide()
            
    def closeEvent(self, event):
        """Clean up on close."""
        self.stop_camera()
        super().closeEvent(event)