# LOGISICA/sentry/ui/dashboard.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
import datetime
import os
from threading import Thread

class Dashboard(tk.Frame):
    def __init__(self, parent, usuario):
        super().__init__(parent)
        self.parent = parent
        self.usuario = usuario
        self.configure(bg="#f0f0f0")
        
        # Variáveis de controle
        self.camera_active = False
        self.cap = None
        self.current_frame = None
        
        # Lista para armazenar histórico
        self.historico_placas = []
        self.fotos_emitidas = []
        
        self.create_widgets()
        self.update_datetime()
    
    def create_widgets(self):
        """Cria todos os widgets do dashboard"""
        
        # Header Frame
        self.create_header()
        
        # Main Content Frame
        main_content = tk.Frame(self, bg="#f0f0f0")
        main_content.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Frame esquerdo (OCR e Camera)
        left_frame = tk.Frame(main_content, bg="#ffffff", relief="raised", bd=2)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # Frame direito (Histórico)
        right_frame = tk.Frame(main_content, bg="#ffffff", relief="raised", bd=2)
        right_frame.pack(side="right", fill="both", expand=False, padx=(5, 0))
        right_frame.configure(width=350)
        right_frame.pack_propagate(False)
        
        # Criar seções
        self.create_ocr_section(left_frame)
        self.create_history_section(right_frame)
    
    def create_header(self):
        """Cria o cabeçalho do dashboard"""
        header_frame = tk.Frame(self, bg="#2c3e50", height=80)
        header_frame.pack(fill="x", padx=10, pady=(10, 5))
        header_frame.pack_propagate(False)
        
        # Info do usuário (esquerda)
        user_frame = tk.Frame(header_frame, bg="#2c3e50")
        user_frame.pack(side="left", fill="y", padx=20, pady=10)
        
        tk.Label(
            user_frame,
            text="SENTRY.INC - Controle de Acesso",
            font=("Helvetica", 16, "bold"),
            fg="white",
            bg="#2c3e50"
        ).pack(anchor="w")
        
        tk.Label(
            user_frame,
            text=f"Usuário: {self.usuario['nome_completo']}",
            font=("Helvetica", 10),
            fg="#ecf0f1",
            bg="#2c3e50"
        ).pack(anchor="w")
        
        # Data/Hora e Logout (direita)
        controls_frame = tk.Frame(header_frame, bg="#2c3e50")
        controls_frame.pack(side="right", fill="y", padx=20, pady=10)
        
        self.datetime_label = tk.Label(
            controls_frame,
            text="",
            font=("Helvetica", 10),
            fg="white",
            bg="#2c3e50"
        )
        self.datetime_label.pack(anchor="e")
        
        logout_btn = tk.Button(
            controls_frame,
            text="Logout",
            command=self.logout,
            bg="#e74c3c",
            fg="white",
            font=("Helvetica", 10, "bold"),
            relief="raised",
            bd=2,
            padx=15
        )
        logout_btn.pack(anchor="e", pady=(5, 0))
    
    def create_ocr_section(self, parent):
        """Cria a seção de OCR e Camera"""
        # Título da seção
        title_frame = tk.Frame(parent, bg="#3498db", height=40)
        title_frame.pack(fill="x", padx=5, pady=5)
        title_frame.pack_propagate(False)
        
        tk.Label(
            title_frame,
            text="OCR - Reconhecimento de Placas",
            font=("Helvetica", 12, "bold"),
            fg="white",
            bg="#3498db"
        ).pack(expand=True)
        
        # Controles da câmera
        controls_frame = tk.Frame(parent, bg="#ffffff")
        controls_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Button(
            controls_frame,
            text="Iniciar Câmera",
            command=self.start_camera,
            bg="#27ae60",
            fg="white",
            font=("Helvetica", 10, "bold"),
            padx=10
        ).pack(side="left", padx=5)
        
        tk.Button(
            controls_frame,
            text="Parar Câmera",
            command=self.stop_camera,
            bg="#e74c3c",
            fg="white",
            font=("Helvetica", 10, "bold"),
            padx=10
        ).pack(side="left", padx=5)
        
        tk.Button(
            controls_frame,
            text="Capturar Foto",
            command=self.capture_photo,
            bg="#f39c12",
            fg="white",
            font=("Helvetica", 10, "bold"),
            padx=10
        ).pack(side="left", padx=5)
        
        tk.Button(
            controls_frame,
            text="Carregar Imagem",
            command=self.load_image,
            bg="#9b59b6",
            fg="white",
            font=("Helvetica", 10, "bold"),
            padx=10
        ).pack(side="left", padx=5)
        
        # Area da câmera/imagem
        camera_frame = tk.Frame(parent, bg="#ecf0f1", relief="sunken", bd=2)
        camera_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.camera_label = tk.Label(
            camera_frame,
            text="Câmera/Imagem aparecerá aqui",
            bg="#ecf0f1",
            font=("Helvetica", 12),
            fg="#7f8c8d"
        )
        self.camera_label.pack(expand=True)
        
        # Resultado do OCR
        ocr_result_frame = tk.Frame(parent, bg="#ffffff")
        ocr_result_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(
            ocr_result_frame,
            text="Resultado OCR:",
            font=("Helvetica", 10, "bold"),
            bg="#ffffff"
        ).pack(anchor="w")
        
        self.ocr_result = tk.Text(
            ocr_result_frame,
            height=3,
            font=("Courier", 10),
            bg="#f8f9fa",
            relief="sunken",
            bd=1
        )
        self.ocr_result.pack(fill="x", pady=5)
        
        # Botão de processar OCR
        tk.Button(
            ocr_result_frame,
            text="Processar OCR",
            command=self.process_ocr,
            bg="#3498db",
            fg="white",
            font=("Helvetica", 10, "bold"),
            padx=20
        ).pack(pady=5)
    
    def create_history_section(self, parent):
        """Cria a seção de histórico"""
        # Notebook para abas
        notebook = ttk.Notebook(parent)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Aba Histórico de Placas
        placas_frame = tk.Frame(notebook, bg="#ffffff")
        notebook.add(placas_frame, text="Histórico Placas")
        
        # Lista de placas
        tk.Label(
            placas_frame,
            text="Placas Detectadas:",
            font=("Helvetica", 10, "bold"),
            bg="#ffffff"
        ).pack(anchor="w", padx=5, pady=(5, 0))
        
        # Listbox com scrollbar
        placas_list_frame = tk.Frame(placas_frame)
        placas_list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        scrollbar_placas = tk.Scrollbar(placas_list_frame)
        scrollbar_placas.pack(side="right", fill="y")
        
        self.placas_listbox = tk.Listbox(
            placas_list_frame,
            yscrollcommand=scrollbar_placas.set,
            font=("Courier", 9),
            bg="#f8f9fa"
        )
        self.placas_listbox.pack(fill="both", expand=True)
        scrollbar_placas.config(command=self.placas_listbox.yview)
        
        # Botões para histórico de placas
        placas_btn_frame = tk.Frame(placas_frame, bg="#ffffff")
        placas_btn_frame.pack(fill="x", padx=5, pady=5)
        
        tk.Button(
            placas_btn_frame,
            text="Limpar",
            command=self.clear_placas_history,
            bg="#e74c3c",
            fg="white",
            font=("Helvetica", 9)
        ).pack(side="left", padx=2)
        
        tk.Button(
            placas_btn_frame,
            text="Exportar",
            command=self.export_placas_history,
            bg="#2ecc71",
            fg="white",
            font=("Helvetica", 9)
        ).pack(side="left", padx=2)
        
        # Aba Fotos Emitidas
        fotos_frame = tk.Frame(notebook, bg="#ffffff")
        notebook.add(fotos_frame, text="Fotos Emitidas")
        
        tk.Label(
            fotos_frame,
            text="Fotos Capturadas:",
            font=("Helvetica", 10, "bold"),
            bg="#ffffff"
        ).pack(anchor="w", padx=5, pady=(5, 0))
        
        # Lista de fotos
        fotos_list_frame = tk.Frame(fotos_frame)
        fotos_list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        scrollbar_fotos = tk.Scrollbar(fotos_list_frame)
        scrollbar_fotos.pack(side="right", fill="y")
        
        self.fotos_listbox = tk.Listbox(
            fotos_list_frame,
            yscrollcommand=scrollbar_fotos.set,
            font=("Courier", 9),
            bg="#f8f9fa"
        )
        self.fotos_listbox.pack(fill="both", expand=True)
        scrollbar_fotos.config(command=self.fotos_listbox.yview)
        
        # Botões para fotos
        fotos_btn_frame = tk.Frame(fotos_frame, bg="#ffffff")
        fotos_btn_frame.pack(fill="x", padx=5, pady=5)
        
        tk.Button(
            fotos_btn_frame,
            text="Limpar",
            command=self.clear_fotos_history,
            bg="#e74c3c",
            fg="white",
            font=("Helvetica", 9)
        ).pack(side="left", padx=2)
        
        tk.Button(
            fotos_btn_frame,
            text="Ver Foto",
            command=self.view_photo,
            bg="#3498db",
            fg="white",
            font=("Helvetica", 9)
        ).pack(side="left", padx=2)
    
    def update_datetime(self):
        """Atualiza data/hora no header"""
        now = datetime.datetime.now()
        datetime_str = now.strftime("%d/%m/%Y - %H:%M:%S")
        self.datetime_label.config(text=datetime_str)
        self.after(1000, self.update_datetime)  # Atualiza a cada segundo
    
    def start_camera(self):
        """Inicia a câmera"""
        try:
            if not self.camera_active:
                self.cap = cv2.VideoCapture(0)
                if self.cap.isOpened():
                    self.camera_active = True
                    self.update_camera()
                else:
                    messagebox.showerror("Erro", "Não foi possível acessar a câmera")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao iniciar câmera: {str(e)}")
    
    def stop_camera(self):
        """Para a câmera"""
        if self.camera_active and self.cap:
            self.camera_active = False
            self.cap.release()
            self.camera_label.config(image="", text="Câmera/Imagem aparecerá aqui")
    
    def update_camera(self):
        """Atualiza o frame da câmera"""
        if self.camera_active and self.cap:
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame
                # Converter para formato Tkinter
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_resized = cv2.resize(frame_rgb, (640, 480))
                image = Image.fromarray(frame_resized)
                photo = ImageTk.PhotoImage(image)
                
                self.camera_label.config(image=photo, text="")
                self.camera_label.image = photo
                
                self.after(30, self.update_camera)  # ~30 FPS
    
    def capture_photo(self):
        """Captura uma foto da câmera"""
        if self.camera_active and self.current_frame is not None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"foto_{timestamp}.jpg"
            
            # Criar diretório se não existir
            os.makedirs("fotos_capturadas", exist_ok=True)
            filepath = os.path.join("fotos_capturadas", filename)
            
            # Salvar foto
            cv2.imwrite(filepath, self.current_frame)
            
            # Adicionar ao histórico
            foto_info = {
                "filename": filename,
                "filepath": filepath,
                "timestamp": timestamp,
                "usuario": self.usuario['username']
            }
            self.fotos_emitidas.append(foto_info)
            
            # Atualizar lista
            display_text = f"{timestamp} - {filename}"
            self.fotos_listbox.insert(0, display_text)
            
            messagebox.showinfo("Sucesso", f"Foto capturada: {filename}")
        else:
            messagebox.showwarning("Aviso", "Câmera não está ativa ou não há frame disponível")
    
    def load_image(self):
        """Carrega uma imagem do computador"""
        file_path = filedialog.askopenfilename(
            title="Selecionar Imagem",
            filetypes=[("Arquivos de Imagem", "*.jpg *.jpeg *.png *.bmp *.tiff")]
        )
        
        if file_path:
            try:
                # Carregar e exibir imagem
                image = cv2.imread(file_path)
                if image is not None:
                    self.current_frame = image
                    
                    # Converter para exibição
                    frame_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    frame_resized = cv2.resize(frame_rgb, (640, 480))
                    pil_image = Image.fromarray(frame_resized)
                    photo = ImageTk.PhotoImage(pil_image)
                    
                    self.camera_label.config(image=photo, text="")
                    self.camera_label.image = photo
                else:
                    messagebox.showerror("Erro", "Não foi possível carregar a imagem")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao carregar imagem: {str(e)}")
    
    def process_ocr(self):
        """Processa OCR na imagem atual (simulado)"""
        if self.current_frame is not None:
            # Simulação de OCR - aqui você integraria com EasyOCR ou Tesseract
            import random
            import string
            
            # Simular detecção de placa
            placas_simuladas = [
                "ABC-1234", "XYZ-5678", "DEF-9012", 
                "GHI-3456", "JKL-7890", "MNO-2468"
            ]
            
            placa_detectada = random.choice(placas_simuladas)
            confianca = round(random.uniform(0.7, 0.99), 2)
            
            # Atualizar resultado OCR
            self.ocr_result.delete(1.0, tk.END)
            resultado = f"Placa detectada: {placa_detectada}\nConfiança: {confianca*100:.1f}%"
            self.ocr_result.insert(1.0, resultado)
            
            # Adicionar ao histórico
            timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            placa_info = {
                "placa": placa_detectada,
                "confianca": confianca,
                "timestamp": timestamp,
                "usuario": self.usuario['username']
            }
            self.historico_placas.append(placa_info)
            
            # Atualizar lista
            display_text = f"{timestamp} - {placa_detectada} ({confianca*100:.1f}%)"
            self.placas_listbox.insert(0, display_text)
            
        else:
            messagebox.showwarning("Aviso", "Nenhuma imagem carregada para processar")
    
    def clear_placas_history(self):
        """Limpa o histórico de placas"""
        if messagebox.askyesno("Confirmar", "Limpar todo o histórico de placas?"):
            self.historico_placas.clear()
            self.placas_listbox.delete(0, tk.END)
    
    def export_placas_history(self):
        """Exporta o histórico de placas"""
        if not self.historico_placas:
            messagebox.showwarning("Aviso", "Nenhum dado para exportar")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Salvar Histórico",
            defaultextension=".txt",
            filetypes=[("Arquivo de Texto", "*.txt")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("SENTRY.INC - Histórico de Placas Detectadas\n")
                    f.write("=" * 50 + "\n\n")
                    for item in reversed(self.historico_placas):
                        f.write(f"Data/Hora: {item['timestamp']}\n")
                        f.write(f"Placa: {item['placa']}\n")
                        f.write(f"Confiança: {item['confianca']*100:.1f}%\n")
                        f.write(f"Usuário: {item['usuario']}\n")
                        f.write("-" * 30 + "\n")
                
                messagebox.showinfo("Sucesso", f"Histórico exportado para: {file_path}")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao exportar: {str(e)}")
    
    def clear_fotos_history(self):
        """Limpa o histórico de fotos"""
        if messagebox.askyesno("Confirmar", "Limpar todo o histórico de fotos?"):
            self.fotos_emitidas.clear()
            self.fotos_listbox.delete(0, tk.END)
    
    def view_photo(self):
        """Visualiza uma foto selecionada"""
        selection = self.fotos_listbox.curselection()
        if selection:
            index = len(self.fotos_emitidas) - 1 - selection[0]  # Lista invertida
            foto_info = self.fotos_emitidas[index]
            
            if os.path.exists(foto_info['filepath']):
                # Abrir em nova janela (implementação básica)
                messagebox.showinfo("Foto", f"Arquivo: {foto_info['filepath']}\nImplementar visualização aqui")
            else:
                messagebox.showerror("Erro", "Arquivo não encontrado")
        else:
            messagebox.showwarning("Aviso", "Selecione uma foto para visualizar")
    
    def logout(self):
        """Realiza logout"""
        if hasattr(self.parent, 'logout'):
            self.stop_camera()  # Para a câmera antes de sair
            self.parent.logout()
        else:
            messagebox.showwarning("Aviso", "Função de logout não encontrada")