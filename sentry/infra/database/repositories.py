# sentry/infra/database/repositories.py
import sqlite3
from sentry.config import Config

class UserRepository:
    def __init__(self):
        self.conn = sqlite3.connect(str(Config.DB_PATH))
        self.conn.row_factory = sqlite3.Row  # Para acessar colunas por nome
    
    def find_by_username(self, username: str):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, username, password_hash, nivel_acesso, nome_completo "
            "FROM usuarios WHERE username = ?",
            (username,)
        )
        return cursor.fetchone()
    
    def close(self):
        self.conn.close()

class VehicleRepository:
    # (Implementação para veículos - adicione posteriormente)
    pass