# LOGISICA/sentry/ui/dashboard.py
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont
from PIL import Image, ImageTk

class Dashboard(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.configure(bg='#f0f2f5')
        self.create_widgets()
    
    def create_widgets(self):
        # Container principal
        self.main_container = tk.Frame(self, bg='#f0f2f5')
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # Menu Lateral
        self.create_sidebar()
        
        # Área de Conteúdo
        self.create_content_area()
    
    def create_sidebar(self):
        sidebar = tk.Frame(
            self.main_container,
            bg='#2c3e50',
            width=250,
            relief=tk.SUNKEN
        )
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        
        # Logo
        logo_frame = tk.Frame(sidebar, bg='#2c3e50', pady=20)
        logo_frame.pack(fill=tk.X)
        
        logo_label = tk.Label(
            logo_frame,
            text="LOGISICA",
            font=('Helvetica', 14, 'bold'),
            fg='white',
            bg='#2c3e50'
        )
        logo_label.pack()
        
        # Itens do Menu
        menu_items = [
            ("Controle de Acesso", self.show_access_control),
            ("Registros", self.show_records),
            ("Cadastros", self.show_registers),
            ("Relatórios", self.show_reports),
            ("Configurações", self.show_settings)
        ]
        
        for text, command in menu_items:
            btn = tk.Button(
                sidebar,
                text=text,
                font=('Helvetica', 10),
                bg='#34495e',
                fg='white',
                bd=0,
                padx=20,
                pady=15,
                anchor='w',
                command=command
            )
            btn.pack(fill=tk.X)
        
        # Botão Sair
        logout_btn = tk.Button(
            sidebar,
            text="Sair",
            font=('Helvetica', 10),
            bg='#e74c3c',
            fg='white',
            bd=0,
            padx=20,
            pady=15,
            anchor='w',
            command=self.parent.show_login
        )
        logout_btn.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_content_area(self):
        self.content_area = tk.Frame(
            self.main_container,
            bg='white',
            padx=20,
            pady=20
        )
        self.content_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Barra superior
        top_bar = tk.Frame(self.content_area, bg='white')
        top_bar.pack(fill=tk.X, pady=(0, 20))
        
        user_label = tk.Label(
            top_bar,
            text=f"Bem-vindo, {self.parent.usuario_logado['nome_completo']}",
            font=('Helvetica', 12),
            bg='white'
        )
        user_label.pack(side=tk.LEFT)
        
        # Área dinâmica
        self.current_frame = tk.Frame(self.content_area, bg='white')
        self.current_frame.pack(fill=tk.BOTH, expand=True)
        
        # Mostrar dashboard inicial
        self.show_dashboard()
    
    def show_dashboard(self):
        """Tela inicial do dashboard"""
        for widget in self.current_frame.winfo_children():
            widget.destroy()
        
        # Widgets do dashboard
        title = tk.Label(
            self.current_frame,
            text="Painel de Controle",
            font=('Helvetica', 16, 'bold'),
            bg='white'
        )
        title.pack(pady=(0, 20))
        
        # Cards de estatísticas
        stats_frame = tk.Frame(self.current_frame, bg='white')
        stats_frame.pack(fill=tk.X, pady=10)
        
        stats = [
            ("Entradas Hoje", "45", "#3498db"),
            ("Saídas Hoje", "32", "#e74c3c"),
            ("Total Veículos", "127", "#2ecc71"),
            ("Alertas", "3", "#f39c12")
        ]
        
        for text, value, color in stats:
            card = tk.Frame(
                stats_frame,
                bg=color,
                padx=15,
                pady=10,
                relief=tk.RAISED,
                bd=1
            )
            card.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
            
            tk.Label(
                card,
                text=text,
                bg=color,
                fg='white',
                font=('Helvetica', 10)
            ).pack()
            
            tk.Label(
                card,
                text=value,
                bg=color,
                fg='white',
                font=('Helvetica', 24, 'bold')
            ).pack()
    
    # Métodos para outras telas (serão implementados)
    def show_access_control(self):
        print("Mostrar controle de acesso")
    
    def show_records(self):
        print("Mostrar registros")
    
    def show_registers(self):
        print("Mostrar cadastros")
    
    def show_reports(self):
        print("Mostrar relatórios")
    
    def show_settings(self):
        print("Mostrar configurações")