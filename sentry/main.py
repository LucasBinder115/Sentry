# LOGISICA/sentry/main.py (atualizado)
import tkinter as tk
from tkinter import ttk
from .auth.login_page import LoginPage
from .ui.splash import SplashScreen
from sentry.ui.dashboard import Dashboard

class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SENTRY.INC - Controle de Acesso")
        self.geometry("1024x768")
        self.resizable(False, False)
        self.style = ttk.Style(self)
        self.configure_theme()
        
        self.splash = SplashScreen(self)
        self.splash.pack(fill=tk.BOTH, expand=True)
        self.after(3000, self.show_login)
    
    def configure_theme(self):
        self.style.theme_use('clam')
    
    def show_login(self):
        self.splash.destroy()
        LoginPage(self).pack(fill=tk.BOTH, expand=True)
    
    def show_main_interface(self):
        """Nova função para mostrar a interface principal após login"""
        # Limpar a tela atual
        for widget in self.winfo_children():
            widget.destroy()
        
        # Adicionar aqui a interface principal
        label = tk.Label(
            self,
            text="Interface Principal - Bem-vindo!",
            font=("Helvetica", 16)
        )
        label.pack(expand=True)

if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()