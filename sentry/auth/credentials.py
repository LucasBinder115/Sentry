# LOGISICA/sentry/auth/credentials.py
import sqlite3
from pathlib import Path
from ..database import DB_PATH

def verify_credentials(username, password):
    """Verifica se as credenciais são válidas"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT password_hash FROM usuarios WHERE username = ?",
            (username,)
        )
        result = cursor.fetchone()
        
        if result and result[0] == password:  # Em produção, usar hash seguro!
            return True
        return False
    except sqlite3.Error as e:
        print(f"Erro ao verificar credenciais: {e}")
        return False
    finally:
        conn.close()