"""SQLite database configuration and initialization."""

import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Database path relative to this file
DB_PATH = Path(__file__).parent / "database.db"

@contextmanager
def get_connection():
    """Get a database connection with context management."""
    conn = None
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row  # Enable row factory for named columns
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def init_db():
    """Initialize database with required tables."""
    try:
        logger.info("Initializing database...")
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript("""
                -- Vehicles table
                CREATE TABLE IF NOT EXISTS vehicles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plate TEXT NOT NULL UNIQUE,
                    model TEXT NOT NULL,
                    color TEXT,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    created_at TEXT NOT NULL
                );

                -- Carriers (transportation companies) table
                CREATE TABLE IF NOT EXISTS carriers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    cnpj TEXT NOT NULL UNIQUE,
                    contact_phone TEXT,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    created_at TEXT NOT NULL
                );

                -- Access logs table
                CREATE TABLE IF NOT EXISTS access_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id INTEGER,
                    type TEXT NOT NULL,  -- ENTRADA or SAÍDA
                    timestamp TEXT NOT NULL,
                    photo_path TEXT,
                    ocr_confidence REAL,
                    plate_text TEXT,
                    notes TEXT,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    FOREIGN KEY(vehicle_id) REFERENCES vehicles(id)
                );

                -- Create indexes
                CREATE INDEX IF NOT EXISTS idx_vehicles_plate 
                ON vehicles(plate);
                
                CREATE INDEX IF NOT EXISTS idx_carriers_cnpj 
                ON carriers(cnpj);
                
                CREATE INDEX IF NOT EXISTS idx_access_logs_vehicle 
                ON access_logs(vehicle_id);
            """)
            conn.commit()
            logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise