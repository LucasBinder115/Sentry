# sentry/infra/database/repositories.py
import sqlite3
from sentry.config import Config

class VehicleRepository:
    def __init__(self):
        self.conn = sqlite3.connect(Config.DB_PATH)
    
    def save_vehicle(self, plate: str, direction: str):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO registros (placa_veiculo, direcao) VALUES (?, ?)",
            (plate, direction)
        )
        self.conn.commit()