# LOGISICA/sentry/main.py
import tkinter as tk
from tkinter import ttk
from .auth.login_page import LoginPage
from .ui.splash import SplashScreen
from sentry.ui.dashboard import Dashboard

class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SENTRY.INC - Controle de Acesso")
        self.geometry("1200x700")
        self.resizable(True, True)
        self.style = ttk.Style(self)
        self.configure_theme()
        
        # Variável para armazenar o usuário logado
        self.usuario_logado = None
        
        self.show_splash()

    def configure_theme(self):
        self.style.theme_use('clam')
        self.style.configure('TFrame', background='#f0f2f5')
        self.style.configure('TLabel', background='#f0f2f5', font=('Helvetica', 10))
    
    def show_splash(self):
        self.splash = SplashScreen(self)
        self.splash.pack(fill=tk.BOTH, expand=True)
        # Exibe a tela de splash por 2.5 segundos antes de mostrar a tela de login
        self.after(2500, self.show_login)

    def show_login(self):
        # Destrói a tela de splash se ela existir
        if self.splash:
            self.splash.destroy()
        
        # Destrói todos os outros widgets para "limpar" a tela
        for widget in self.winfo_children():
            widget.destroy()

        LoginPage(self).pack(fill=tk.BOTH, expand=True)
    
    def show_dashboard(self, usuario):
        """Mostra a interface principal (Dashboard) após o login."""
        self.usuario_logado = usuario
        
        # Limpa a tela antes de mostrar o Dashboard
        for widget in self.winfo_children():
            widget.destroy()
        
        # Exibe a interface do Dashboard
        Dashboard(self, usuario).pack(fill=tk.BOTH, expand=True)

if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()