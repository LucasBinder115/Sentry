"""Base repository class for database operations."""

import logging
from typing import List, Dict, Any, Optional
import sqlite3
from .database_manager import DatabaseManager

class BaseRepository:
    """Base repository with common database operations."""
    
    def __init__(self, table_name: str):
        """Initialize base repository."""
        self.table_name = table_name
        self.logger = logging.getLogger(__name__)
        self.db = DatabaseManager()

    def create(self, **fields) -> int:
        """Create a new record."""
        field_names = ', '.join(fields.keys())
        placeholders = ', '.join(['?' for _ in fields])
        query = f"INSERT INTO {self.table_name} ({field_names}) VALUES ({placeholders})"
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(fields.values()))
                conn.commit()
                record_id = cursor.lastrowid
                
                # Log activity
                self.db.log_activity(
                    'CREATE',
                    f'New {self.table_name} record created',
                    self.table_name,
                    record_id
                )
                
                return record_id
        except Exception as e:
            self.logger.error(f"Error creating record: {e}")
            raise

    def get_by_id(self, id: int) -> Optional[sqlite3.Row]:
        """Retrieve a record by ID."""
        query = f"SELECT * FROM {self.table_name} WHERE id = ?"

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (id,))
                return cursor.fetchone()
        except Exception as e:
            self.logger.error(f"Error retrieving record {id}: {e}")
            raise

    def get_all(self) -> List[sqlite3.Row]:
        """Retrieve all active records."""
        query = f"SELECT * FROM {self.table_name} WHERE status = 'ACTIVE' ORDER BY created_at DESC"

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Error retrieving records: {e}")
            raise

    def update(self, id: int, **fields) -> bool:
        """Update a record by ID."""
        set_clause = ', '.join([f"{k} = ?" for k in fields.keys()])
        values = list(fields.values()) + [id]

        query = f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?"

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, values)
                conn.commit()
                
                if cursor.rowcount > 0:
                    # Log activity
                    self.db.log_activity(
                        'UPDATE',
                        f'Updated {self.table_name} record {id}',
                        self.table_name,
                        id
                    )
                    return True
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating record {id}: {e}")
            raise

    def delete(self, id: int) -> bool:
        """Soft delete a record by setting status to INACTIVE."""
        result = self.update(id, status='INACTIVE')
        if result:
            # Log activity
            self.db.log_activity(
                'DELETE',
                f'Deleted {self.table_name} record {id}',
                self.table_name,
                id
            )
        return result

    def execute_query(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Execute a custom query with parameters."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Error executing query: {e}")
            raise
            
    def search(self, **criteria) -> List[sqlite3.Row]:
        """Search records with multiple criteria."""
        conditions = []
        values = []
        
        for field, value in criteria.items():
            if value is not None:
                conditions.append(f"{field} LIKE ?")
                values.append(f"%{value}%")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM {self.table_name} WHERE {where_clause} AND status = 'ACTIVE'"
        
        return self.execute_query(query, tuple(values))