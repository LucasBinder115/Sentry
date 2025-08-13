# LOGISICA/sentry/database.py
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "registros.db"

def init_db():
    """Inicializa o banco de dados com as tabelas necessárias"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tabela de usuários
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nivel_acesso INTEGER DEFAULT 1,
        nome_completo TEXT,
        email TEXT,
        ativo INTEGER DEFAULT 1
    )
    """)
    
    # Tabela de registros de acesso
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS registros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        placa_veiculo TEXT NOT NULL,
        data_hora TEXT NOT NULL,
        direcao TEXT CHECK(direcao IN ('entrada', 'saida')),
        usuario_id INTEGER,
        foto_path TEXT,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    )
    """)
    
    # Inserir usuário admin padrão se não existir
    cursor.execute("""
    INSERT OR IGNORE INTO usuarios (username, password_hash, nivel_acesso, nome_completo)
    VALUES ('admin', 'admin123', 3, 'Administrador Padrão')
    """)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print(f"Banco de dados inicializado em: {DB_PATH}")