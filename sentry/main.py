# LOGISICA/sentry/main.py
import tkinter as tk
from tkinter import ttk, messagebox
from .auth.login_page import LoginPage
from .ui.splash import SplashScreen
from .ui.dashboard import Dashboard
from .config import Config

class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SENTRY.INC - Controle de Acesso")
        self.geometry("1200x700")
        self.resizable(True, True)
        self.style = ttk.Style(self)
        self.configure_theme()
        
        # Centralizar janela
        self.center_window()
        
        # Variável para armazenar o usuário logado
        self.usuario_logado = None
        self.current_frame = None
        
        # Configurar protocolo de fechamento
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.show_splash()
    
    def configure_theme(self):
        """Configura o tema da aplicação"""
        self.style.theme_use('clam')
        self.style.configure('TFrame', background="#4676be")
        self.style.configure('TLabel', background="#2170e6", font=('Helvetica', 10))
    
    def center_window(self):
        """Centraliza a janela na tela"""
        self.update_idletasks()
        width = 1200
        height = 700
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def show_splash(self):
        """Exibe a tela de splash"""
        try:
            self.current_frame = SplashScreen(self)
            self.current_frame.pack(fill=tk.BOTH, expand=True)
            # Exibe a tela de splash por 2.5 segundos antes de mostrar a tela de login
            self.after(2500, self.show_login)
        except ImportError:
            # Se não conseguir importar SplashScreen, vai direto para login
            print("Aviso: SplashScreen não encontrado, indo direto para login")
            self.show_login()
    
    def show_login(self):
        """Exibe a tela de login"""
        # Destrói o frame atual se existir
        if self.current_frame:
            self.current_frame.destroy()
        
        # Limpa todos os widgets para garantir tela limpa
        for widget in self.winfo_children():
            widget.destroy()
        
        # Reset do usuário logado
        self.usuario_logado = None
        
        # Cria e exibe a tela de login
        self.current_frame = LoginPage(self)
        self.current_frame.pack(fill=tk.BOTH, expand=True)
    
    def show_dashboard(self, usuario):
        """Mostra a interface principal (Dashboard) após o login"""
        try:
            # Armazena o usuário logado
            self.usuario_logado = usuario
            
            # Destrói o frame atual se existir
            if self.current_frame:
                self.current_frame.destroy()
            
            # Limpa a tela antes de mostrar o Dashboard
            for widget in self.winfo_children():
                widget.destroy()
            
            # Exibe a interface do Dashboard
            self.current_frame = Dashboard(self, usuario)
            self.current_frame.pack(fill=tk.BOTH, expand=True)
            
            print(f"Dashboard carregado para usuário: {usuario.get('username', 'Desconhecido')}")
            
        except Exception as e:
            print(f"Erro ao carregar dashboard: {e}")
            messagebox.showerror(
                "Erro", 
                f"Erro ao carregar dashboard: {str(e)}\nRetornando ao login."
            )
            self.show_login()
    
    def logout(self):
        """Realiza o logout do usuário"""
        if self.usuario_logado:
            response = messagebox.askyesno(
                "Logout", 
                f"Deseja realmente fazer logout?\nUsuário: {self.usuario_logado.get('username', 'Desconhecido')}"
            )
            if response:
                print(f"Logout realizado para usuário: {self.usuario_logado.get('username', 'Desconhecido')}")
                self.show_login()
        else:
            self.show_login()
    
    def on_closing(self):
        """Manipula o evento de fechamento da janela"""
        if self.usuario_logado:
            response = messagebox.askyesno(
                "Fechar Sistema", 
                "Deseja realmente fechar o sistema?"
            )
            if response:
                print("Sistema encerrado pelo usuário")
                self.destroy()
        else:
            self.destroy()
    
    def get_current_user(self):
        """Retorna o usuário atualmente logado"""
        return self.usuario_logado
    
    def update_user_info(self, usuario):
        """Atualiza as informações do usuário logado"""
        self.usuario_logado = usuario
    
    def restart_application(self):
        """Reinicia a aplicação"""
        response = messagebox.askyesno(
            "Reiniciar Sistema", 
            "Deseja reiniciar o sistema?"
        )
        if response:
            print("Reiniciando sistema...")
            self.show_splash()

def main():
    """Função principal para iniciar a aplicação"""
    try:
        app = MainApplication()
        print("Sistema SENTRY.INC iniciado com sucesso!")
        app.mainloop()
    except Exception as e:
        print(f"Erro fatal ao iniciar aplicação: {e}")
        messagebox.showerror("Erro Fatal", f"Erro ao iniciar aplicação:\n{str(e)}")

if __name__ == "__main__":
    main()