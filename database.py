import sqlite3
from datetime import datetime

DB_NAME = "registros.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placa TEXT NOT NULL,
            data_hora TEXT NOT NULL,
            tipo TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def registrar_movimento(placa, tipo):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    data_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cur.execute("INSERT INTO registros (placa, data_hora, tipo) VALUES (?, ?, ?)",
                (placa, data_hora, tipo))
    conn.commit()
    conn.close()
