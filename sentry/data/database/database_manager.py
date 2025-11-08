"""Database connection manager with connection pooling and error handling."""

import sqlite3
from typing import Optional, Any
from contextlib import contextmanager
from threading import Lock
import logging
import os
from datetime import datetime

class DatabaseManager:
    """Manages database connections and provides utility functions."""
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        """Initialize the database manager."""
        self.logger = logging.getLogger(__name__)
        
        # Setup database directory and path
        self.data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'database'))
        self.db_path = os.path.join(self.data_dir, 'sentry.db')
        
        # Initialize connection pool
        self.connection_pool = []
        self.max_connections = 5
        
        # Ensure directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.logger.info(f"Database path: {self.db_path}")
        self._ensure_database()
    
    def _ensure_database(self):
        """Ensure database and tables exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # Create tables (all required)
            self._create_tables(cursor)
            conn.commit()
            # Ensure new columns exist (simple migrations)
            try:
                self._ensure_columns(cursor)
                conn.commit()
            except Exception:
                pass
    
    def _create_tables(self, cursor):
        """Create all required tables."""
        # Vehicles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plate TEXT UNIQUE NOT NULL,
                model TEXT NOT NULL,
                color TEXT,
                status TEXT DEFAULT 'ACTIVE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Merchandise table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS merchandise (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                quantity INTEGER NOT NULL DEFAULT 0,
                unit TEXT NOT NULL,
                status TEXT DEFAULT 'ACTIVE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Carriers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS carriers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                cnpj TEXT UNIQUE,
                contact TEXT,
                status TEXT DEFAULT 'ACTIVE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Access logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER,
                detected_plate TEXT,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                carrier_id INTEGER,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles (id),
                FOREIGN KEY (carrier_id) REFERENCES carriers (id)
            )
        """)

        # Activity logs table for general system activity
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_type TEXT NOT NULL,
                description TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create triggers for updated_at
        self._create_update_trigger(cursor, "vehicles")
        self._create_update_trigger(cursor, "merchandise")
        self._create_update_trigger(cursor, "carriers")

    def close_connections(self):
        """Close all connections in the pool."""
        while self.connection_pool:
            conn = self.connection_pool.pop()
            try:
                conn.close()
            except Exception as e:
                self.logger.error(f"Error closing connection: {e}")
    
    @contextmanager
    def get_connection(self):
        """Get a database connection from the pool."""
        connection = None
        try:
            # Create data directory if it doesn't exist
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Try to get an existing connection from the pool
            if self.connection_pool:
                connection = self.connection_pool.pop()
                try:
                    # Test the connection
                    connection.execute("SELECT 1")
                except Exception:
                    # Connection is dead, close it and create a new one
                    try:
                        connection.close()
                    except Exception:
                        pass
                    connection = None
            
            if connection is None:
                # Create new connection
                connection = sqlite3.connect(
                    self.db_path,
                    detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                    timeout=20  # Increase timeout for busy database
                )
                connection.row_factory = sqlite3.Row
                
                # Enable foreign keys
                connection.execute("PRAGMA foreign_keys = ON")
                
                # Set journal mode to WAL for better concurrency
                connection.execute("PRAGMA journal_mode = WAL")
                
                # Set synchronous mode to NORMAL for better performance
                connection.execute("PRAGMA synchronous = NORMAL")
            
            yield connection
            
            # Return connection to pool if it's still good
            try:
                connection.execute("SELECT 1")
                if len(self.connection_pool) < self.max_connections:
                    self.connection_pool.append(connection)
                else:
                    connection.close()
            except Exception:
                # Connection is dead, close it
                try:
                    connection.close()
                except Exception:
                    pass
                
        except Exception as e:
            self.logger.error(f"Database error: {str(e)}")
            if connection:
                try:
                    connection.rollback()
                    connection.close()
                except Exception:
                    pass
            raise sqlite3.Error(f"Database error: {str(e)}")

    def _has_column(self, cursor, table: str, column: str) -> bool:
        cursor.execute(f"PRAGMA table_info({table})")
        return any(row[1] == column for row in cursor.fetchall())

    def _ensure_columns(self, cursor):
        """Add new columns if they don't exist yet (SQLite migrations)."""
        # access_logs.carrier_id
        try:
            if not self._has_column(cursor, 'access_logs', 'carrier_id'):
                cursor.execute("ALTER TABLE access_logs ADD COLUMN carrier_id INTEGER")
        except Exception:
            pass
        # merchandise.category
        try:
            if not self._has_column(cursor, 'merchandise', 'category'):
                cursor.execute("ALTER TABLE merchandise ADD COLUMN category TEXT")
        except Exception:
            pass
        # vehicles lat/lon
        try:
            if not self._has_column(cursor, 'vehicles', 'lat'):
                cursor.execute("ALTER TABLE vehicles ADD COLUMN lat REAL")
        except Exception:
            pass
        try:
            if not self._has_column(cursor, 'vehicles', 'lon'):
                cursor.execute("ALTER TABLE vehicles ADD COLUMN lon REAL")
        except Exception:
            pass
        # carriers lat/lon
        try:
            if not self._has_column(cursor, 'carriers', 'lat'):
                cursor.execute("ALTER TABLE carriers ADD COLUMN lat REAL")
        except Exception:
            pass
        try:
            if not self._has_column(cursor, 'carriers', 'lon'):
                cursor.execute("ALTER TABLE carriers ADD COLUMN lon REAL")
        except Exception:
            pass
    
    def _create_update_trigger(self, cursor, table_name):
        """Create an update trigger for the updated_at column."""
        cursor.execute(f"""
            CREATE TRIGGER IF NOT EXISTS update_{table_name}_timestamp 
            AFTER UPDATE ON {table_name}
            BEGIN
                UPDATE {table_name} 
                SET updated_at = CURRENT_TIMESTAMP 
                WHERE id = NEW.id;
            END;
        """)
            
    def execute_query(self, query: str, params: tuple = None) -> list:
        """Execute a query and return all results."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
    
    def execute_update(self, query: str, params: tuple = None) -> bool:
        """Execute an update query."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Update error: {e}")
            return False
    
    def log_activity(self, activity_type: str, description: str, 
                    entity_type: str, entity_id: Optional[int] = None,
                    user_id: Optional[int] = None):
        """Log an activity in the system."""
        query = """
            INSERT INTO activity_logs 
            (activity_type, description, entity_type, entity_id, user_id)
            VALUES (?, ?, ?, ?, ?)
        """
        self.execute_update(query, (activity_type, description, entity_type, entity_id, user_id))
    
    def get_recent_activities(self, limit: int = 10) -> list:
        """Get recent activity logs."""
        query = """
            SELECT * FROM activity_logs
            ORDER BY created_at DESC
            LIMIT ?
        """
        return self.execute_query(query, (limit,))
    
    def backup_database(self, backup_path: Optional[str] = None) -> bool:
        """Create a backup of the database."""
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(
                os.path.dirname(self.db_path),
                f'backup_{timestamp}.db'
            )
            
        try:
            with self.get_connection() as conn:
                backup = sqlite3.connect(backup_path)
                conn.backup(backup)
                backup.close()
                return True
        except Exception as e:
            self.logger.error(f"Backup error: {e}")
            return False