# main.py - Aplicação principal
import tkinter as tk
from tkinter import ttk, messagebox

class LoginPage(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.configure(bg="#f5f5f5")
        self.create_widgets()
    
    def create_widgets(self):
        # Frame principal
        main_frame = tk.Frame(self, bg="#f5f5f5", padx=20, pady=20)
        main_frame.pack(expand=True)
        
        # Título
        title_label = tk.Label(
            main_frame,
            text="SENTRY.INC - Login",
            font=("Helvetica", 16, "bold"),
            bg="#f5f5f5"
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Campo de usuário
        user_label = tk.Label(
            main_frame,
            text="Usuário:",
            font=("Helvetica", 10),
            bg="#f5f5f5"
        )
        user_label.grid(row=1, column=0, sticky="e", padx=(0, 5))
        
        self.user_entry = ttk.Entry(
            main_frame,
            font=("Helvetica", 10),
            width=25
        )
        self.user_entry.grid(row=1, column=1, pady=5)
        
        # Campo de senha
        pass_label = tk.Label(
            main_frame,
            text="Senha:",
            font=("Helvetica", 10),
            bg="#f5f5f5"
        )
        pass_label.grid(row=2, column=0, sticky="e", padx=(0, 5))
        
        self.pass_entry = ttk.Entry(
            main_frame,
            font=("Helvetica", 10),
            width=25,
            show="*"
        )
        self.pass_entry.grid(row=2, column=1, pady=5)
        
        # Botão de login
        login_btn = ttk.Button(
            main_frame,
            text="Entrar",
            command=self.attempt_login
        )
        login_btn.grid(row=3, column=1, pady=15, sticky="e")
        
        # Focar no campo de usuário
        self.user_entry.focus_set()
        
        # Bind Enter para login
        self.pass_entry.bind("<Return>", lambda e: self.attempt_login())
        self.user_entry.bind("<Return>", lambda e: self.pass_entry.focus_set())
    
    def attempt_login(self):
        username = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()
        
        # Verificar credenciais hardcoded
        if self.verify_credentials(username, password):
            usuario = {
                "username": username,
                "nome_completo": "Lucas Binder"
            }
            self.parent.show_dashboard(usuario)
        else:
            messagebox.showerror(
                "Login falhou",
                "Usuário ou senha incorretos"
            )
            self.pass_entry.delete(0, tk.END)
            self.pass_entry.focus_set()

    def verify_credentials(self, username, password):
        """Verifica as credenciais de login"""
        # Credencial válida: usuário "Lucas" e senha "123456"
        return username == "Lucas" and password == "123456"


class DashboardPage(tk.Frame):
    def __init__(self, parent, usuario):
        super().__init__(parent)
        self.parent = parent
        self.usuario = usuario
        self.configure(bg="#f0f0f0")
        self.create_widgets()
    
    def create_widgets(self):
        # Frame principal
        main_frame = tk.Frame(self, bg="#f0f0f0", padx=30, pady=30)
        main_frame.pack(expand=True, fill="both")
        
        # Título do Dashboard
        title_label = tk.Label(
            main_frame,
            text="SENTRY.INC - Dashboard",
            font=("Helvetica", 18, "bold"),
            bg="#f0f0f0"
        )
        title_label.pack(pady=(0, 20))
        
        # Mensagem de boas-vindas
        welcome_label = tk.Label(
            main_frame,
            text=f"Bem-vindo, {self.usuario['nome_completo']}!",
            font=("Helvetica", 14),
            bg="#f0f0f0"
        )
        welcome_label.pack(pady=(0, 30))
        
        # Informações do usuário
        info_frame = tk.Frame(main_frame, bg="#f0f0f0")
        info_frame.pack(pady=(0, 20))
        
        tk.Label(
            info_frame,
            text="Informações da Sessão:",
            font=("Helvetica", 12, "bold"),
            bg="#f0f0f0"
        ).pack(anchor="w")
        
        tk.Label(
            info_frame,
            text=f"Usuário: {self.usuario['username']}",
            font=("Helvetica", 10),
            bg="#f0f0f0"
        ).pack(anchor="w", pady=(5, 0))
        
        tk.Label(
            info_frame,
            text=f"Nome: {self.usuario['nome_completo']}",
            font=("Helvetica", 10),
            bg="#f0f0f0"
        ).pack(anchor="w")
        
        # Botões do dashboard
        buttons_frame = tk.Frame(main_frame, bg="#f0f0f0")
        buttons_frame.pack(pady=20)
        
        # Botão de exemplo
        ttk.Button(
            buttons_frame,
            text="Função 1",
            command=self.funcao_exemplo
        ).pack(side="left", padx=5)
        
        ttk.Button(
            buttons_frame,
            text="Função 2",
            command=self.funcao_exemplo
        ).pack(side="left", padx=5)
        
        # Botão de logout
        logout_btn = ttk.Button(
            main_frame,
            text="Logout",
            command=self.logout
        )
        logout_btn.pack(pady=(30, 0))
    
    def funcao_exemplo(self):
        messagebox.showinfo("Info", "Função do dashboard executada!")
    
    def logout(self):
        response = messagebox.askyesno(
            "Logout", 
            "Deseja realmente fazer logout?"
        )
        if response:
            self.parent.show_login()


class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SENTRY.INC - Sistema de Login")
        self.geometry("800x600")
        self.resizable(True, True)
        
        # Centralizar janela
        self.center_window()
        
        # Inicializar com tela de login
        self.current_frame = None
        self.show_login()
    
    def center_window(self):
        """Centraliza a janela na tela"""
        self.update_idletasks()
        width = 800
        height = 600
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def show_login(self):
        """Mostra a tela de login"""
        if self.current_frame:
            self.current_frame.destroy()
        
        self.current_frame = LoginPage(self)
        self.current_frame.pack(fill="both", expand=True)
    
    def show_dashboard(self, usuario):
        """Mostra o dashboard após login bem-sucedido"""
        if self.current_frame:
            self.current_frame.destroy()
        
        self.current_frame = DashboardPage(self, usuario)
        self.current_frame.pack(fill="both", expand=True)


if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()