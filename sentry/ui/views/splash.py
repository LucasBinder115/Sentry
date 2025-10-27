# LOGISICA/sentry/ui/views/splash.py

from PyQt5.QtWidgets import QSplashScreen, QApplication
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter, QFont, QColor, QBrush, QPen
import sys
import os
from pathlib import Path

class ModernSplashScreen(QSplashScreen):
    """
    Splash screen moderno e elegante para SENTRY.INC
    """
    
    # Sinal emitido quando o splash termina
    splash_finished = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configurar splash screen
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Criar pixmap personalizado
        self.create_splash_pixmap()
        
        # Configurar mensagem
        self.showMessage(
            "SENTRY.INC\nSistema de Controle de Acesso Veicular\n\nCarregando...",
            Qt.AlignCenter | Qt.AlignBottom,
            QColor(255, 255, 255)  # Branco
        )
        
        # Timer para auto-fechar
        self.timer = QTimer()
        self.timer.timeout.connect(self.close_splash)
        self.timer.setSingleShot(True)
        
    def create_splash_pixmap(self):
        """Cria o pixmap personalizado do splash screen."""
        # Dimensões do splash
        width, height = 500, 400
        
        # Criar pixmap
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)
        
        # Criar painter
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Fundo gradiente
        gradient = QBrush(QColor(26, 35, 126))  # Cor primária do sistema
        painter.fillRect(0, 0, width, height, gradient)
        
        # Borda arredondada
        painter.setPen(QPen(QColor(255, 255, 255, 50), 2))
        painter.drawRoundedRect(1, 1, width-2, height-2, 10, 10)
        
        # Logo/Título
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setFont(QFont("Segoe UI", 24, QFont.Bold))
        painter.drawText(50, 100, "SENTRY.INC")
        
        # Subtítulo
        painter.setFont(QFont("Segoe UI", 12))
        painter.drawText(50, 130, "Sistema de Controle de Acesso Veicular")
        
        # Linha decorativa
        painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
        painter.drawLine(50, 150, width-50, 150)
        
        # Versão
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(50, height-50, "Versão 2.0.0")
        
        painter.end()
        
        # Definir pixmap
        self.setPixmap(pixmap)
        
    def start_timer(self, duration_ms=3000):
        """Inicia o timer para fechar o splash."""
        self.timer.start(duration_ms)
        
    def close_splash(self):
        """Fecha o splash screen."""
        self.splash_finished.emit()
        self.close()
        
    def mousePressEvent(self, event):
        """Permite fechar o splash clicando nele."""
        if event.button() == Qt.LeftButton:
            self.close_splash()
            
    def keyPressEvent(self, event):
        """Permite fechar o splash com ESC."""
        if event.key() == Qt.Key_Escape:
            self.close_splash()
        else:
            super().keyPressEvent(event)

# Função de conveniência para criar splash screen
def create_splash_screen(duration_ms=3000):
    """
    Cria e exibe um splash screen.
    
    Args:
        duration_ms: Duração em milissegundos antes de fechar automaticamente
        
    Returns:
        ModernSplashScreen: Instância do splash screen
    """
    splash = ModernSplashScreen()
    splash.start_timer(duration_ms)
    splash.show()
    
    # Processar eventos para garantir renderização
    QApplication.processEvents()
    
    return splash

if __name__ == "__main__":
    # Teste do splash screen
    app = QApplication(sys.argv)
    
    splash = create_splash_screen(3000)
    
    # Simular carregamento
    import time
    time.sleep(3)
    
    app.quit()