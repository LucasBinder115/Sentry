# sentry/config.py (atualizado)
import os
from pathlib import Path

# Caminho base: diretório do projeto (LOGISICA/)
BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    # Configurações de banco de dados
    DB_PATH = BASE_DIR / "data" / "registros.db"
    
    # ... (restante das configurações permanece igual)
    
    @classmethod
    def load_env(cls):
        """Carrega configurações do arquivo .env"""
        env_path = BASE_DIR / ".env"
        if env_path.exists():
            from dotenv import load_dotenv
            load_dotenv(env_path)
            
            # Atualiza caminhos se especificados no .env
            if os.getenv("DB_PATH"):
                cls.DB_PATH = BASE_DIR / os.getenv("DB_PATH")

# Carrega as configurações do ambiente
Config.load_env()