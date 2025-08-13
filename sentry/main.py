# LOGISICA/sentry/main.py
import tkinter as tk
from tkinter import ttk
from .auth.login_page import LoginPage
from .ui.splash import SplashScreen

class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LOGISICA - Controle de Acesso")
        self.geometry("1024x768")
        self.resizable(False, False)
        
        # Configuração do tema
        self.style = ttk.Style(self)
        self.configure_theme()
        
        # Mostrar tela de splash
        self.splash = SplashScreen(self)
        self.splash.pack(fill=tk.BOTH, expand=True)
        
        # Após 3 segundos, mostrar login
        self.after(3000, self.show_login)
    
    def configure_theme(self):
        """Configura o tema visual da aplicação"""
        self.style.theme_use('clam')
        # (Carregar configurações do style.json depois)
    
    def show_login(self):
        """Transição para a tela de login"""
        self.splash.destroy()
        LoginPage(self).pack(fill=tk.BOTH, expand=True)

if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()