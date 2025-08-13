# LOGISICA/sentry/ui/splash.py
import tkinter as tk
from tkinter import ttk
import time

class SplashScreen(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        
        self.configure(bg="#2c3e50")
        self.load_widgets()
    
    def load_widgets(self):
        # Logo e título
        self.logo_label = tk.Label(
            self, 
            text="LOGISICA", 
            font=("Helvetica", 24, "bold"), 
            fg="#ecf0f1", 
            bg="#2c3e50"
        )
        self.logo_label.pack(pady=50)
        
        # Versão
        self.version_label = tk.Label(
            self,
            text="Versão 1.0",
            font=("Helvetica", 10),
            fg="#bdc3c7",
            bg="#2c3e50"
        )
        self.version_label.pack(pady=10)
        
        # Barra de progresso
        self.progress = ttk.Progressbar(
            self,
            orient=tk.HORIZONTAL,
            length=300,
            mode='determinate'
        )
        self.progress.pack(pady=20)
        
        # Atualizar progresso
        self.update_progress()
    
    def update_progress(self):
        for i in range(101):
            self.progress['value'] = i
            self.update()
            time.sleep(0.02)