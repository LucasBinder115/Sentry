# sentry/ui/views/ocr_camera_view.py - Implementação mínima funcional
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import pyqtSignal

class OCRCameraView(QWidget):
    """View mínima para câmera OCR - placeholder para implementação futura"""
    
    # Signals para comunicação com presenter
    plate_detected = pyqtSignal(str)
    camera_error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        label = QLabel("Interface de Câmera OCR - Em desenvolvimento")
        layout.addWidget(label)
        self.setLayout(layout)
    
    def start_camera(self):
        """Iniciar câmera - placeholder"""
        print("Camera started - placeholder")
    
    def stop_camera(self):
        """Parar câmera - placeholder"""
        print("Camera stopped - placeholder")