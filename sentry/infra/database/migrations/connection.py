# LOGISICA/sentry/infra/database/migrations/connection.py
import sqlite3
from pathlib import Path

# ---------- CONFIGURAÇÃO FIXA SQLITE ----------
DB_FILE = Path(__file__).with_name("sentry_migrations.db")
# alternativa absoluta: DB_FILE = Path("/var/lib/sentry/migrations.db")

def get_sqlite_connection():
    """
    Retorna uma conexão sqlite3 pronta para uso.
    Isola cada transação (isolation_level=None) para que
    os commits sejam explícitos.
    """
    conn = sqlite3.connect(DB_FILE, isolation_level=None)
    conn.row_factory = sqlite3.Row  # acesso por nome de coluna
    return conn

# ---------- FACILITADOR PARA MIGRAÇÕES ----------
def cursor():
    """Context manager que devolve um cursor já dentro de uma transação."""
    conn = get_sqlite_connection()
    try:
        cur = conn.cursor()
        cur.execute("BEGIN")  # inicia transação explícita
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()