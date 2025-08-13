import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from detector import detectar_placa
from database import init_db, registrar_movimento

def capturar_e_registrar():
    placa, erro = detectar_placa()

    if erro:
        resultado_label.config(text=f"❌ {erro}")
    else:
        tipo = tipo_var.get()
        registrar_movimento(placa, tipo)
        resultado_label.config(text=f"✅ {tipo.title()} registrada: {placa}")

# Inicia banco
init_db()

# Inicia GUI
app = tk.Tk()
app.title("Sentry - Controle de Acesso Logístico")
app.geometry("500x400")
app.resizable(False, False)

# Logo
try:
    logo_img = Image.open("static/logo.png").resize((200, 100))
    logo = ImageTk.PhotoImage(logo_img)
    logo_label = tk.Label(app, image=logo)
    logo_label.pack(pady=10)
except:
    logo_label = tk.Label(app, text="Sentry", font=("Arial", 20))
    logo_label.pack(pady=20)

# Seleção de tipo de movimento
tipo_var = tk.StringVar(value="entrada")
frame_tipo = tk.Frame(app)
tk.Radiobutton(frame_tipo, text="Entrada", variable=tipo_var, value="entrada").pack(side="left", padx=10)
tk.Radiobutton(frame_tipo, text="Saída", variable=tipo_var, value="saida").pack(side="left", padx=10)
frame_tipo.pack(pady=10)

# Botão principal
botao = tk.Button(app, text="📷 Capturar Placa", command=capturar_e_registrar, font=("Arial", 12), width=25)
botao.pack(pady=20)

# Resultado
resultado_label = tk.Label(app, text="", font=("Arial", 12), fg="blue")
resultado_label.pack(pady=10)

# Inicia loop
app.mainloop()
