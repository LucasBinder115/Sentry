# LOGISICA/sentry/auth/login_page.py
import tkinter as tk
from tkinter import ttk, messagebox
from .credentials import verify_credentials
import sqlite3 # Importação necessária
# Importe DB_PATH, se estiver em outro arquivo
# from ..database.db_config import DB_PATH 

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
    
    def attempt_login(self):
        username = self.user_entry.get()
        password = self.pass_entry.get()
        
        if verify_credentials(username, password):
            # Obter dados do usuário
            usuario = {
                "username": username,
                "nome_completo": self.get_user_fullname(username)
            }
            self.parent.show_dashboard(usuario)
        else:
            messagebox.showerror(
                "Login falhou",
                "Usuário ou senha incorretos"
            )
            self.pass_entry.delete(0, tk.END)

    def get_user_fullname(self, username):
        """Obtém o nome completo do usuário do banco de dados"""
        # A constante DB_PATH precisa ser definida ou importada
        DB_PATH = "caminho_para_seu_banco_de_dados.db" 
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT nome_completo FROM usuarios WHERE username = ?",
                (username,)
            )
            result = cursor.fetchone()
            return result[0] if result else username
        except sqlite3.Error:
            return username