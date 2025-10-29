"""Base repository with common database operations."""

import sqlite3
import logging
from typing import List, Optional, Any, Dict
from datetime import datetime

from .database import get_connection

class BaseRepository:
    """Base repository implementing common CRUD operations."""

    def __init__(self, table_name: str):
        """Initialize repository with table name."""
        self.table_name = table_name
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def create(self, **fields) -> int:
        """Insert a new record and return its ID."""
        fields['created_at'] = datetime.now().isoformat()
        
        placeholders = ', '.join(['?' for _ in fields])
        columns = ', '.join(fields.keys())
        values = list(fields.values())

        query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"

        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, values)
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            self.logger.error(f"Error creating record in {self.table_name}: {e}")
            raise

    def get_by_id(self, id: int) -> Optional[sqlite3.Row]:
        """Retrieve a record by ID."""
        query = f"SELECT * FROM {self.table_name} WHERE id = ?"

        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (id,))
                return cursor.fetchone()
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving record {id}: {e}")
            raise

    def get_all(self) -> List[sqlite3.Row]:
        """Retrieve all active records."""
        query = f"SELECT * FROM {self.table_name} WHERE status = 'ACTIVE'"

        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                return cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving records: {e}")
            raise

    def update(self, id: int, **fields) -> bool:
        """Update a record by ID."""
        set_clause = ', '.join([f"{k} = ?" for k in fields.keys()])
        values = list(fields.values()) + [id]

        query = f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?"

        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, values)
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            self.logger.error(f"Error updating record {id}: {e}")
            raise

    def delete(self, id: int) -> bool:
        """Soft delete a record by setting status to INACTIVE."""
        return self.update(id, status='INACTIVE')

    def execute_query(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Execute a custom query with parameters."""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.error(f"Error executing query: {e}")
            raise