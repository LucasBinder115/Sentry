"""Merchandise repository for database operations."""

import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base_repository import BaseRepository

class MerchandiseRepository(BaseRepository):
    """Repository for merchandise-related database operations."""

    def __init__(self):
        """Initialize merchandise repository."""
        super().__init__('merchandise')
        self._init_table()

    def _init_table(self):
        """Initialize the merchandise table if it doesn't exist."""
        query = """
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
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error creating merchandise table: {e}")
            raise

    def create_merchandise(self, name: str, unit: str, quantity: int = 0, description: str = None) -> Dict[str, Any]:
        """Create a new merchandise record."""
        try:
            merchandise_id = self.create(
                name=name,
                description=description,
                quantity=quantity,
                unit=unit,
                status='ACTIVE'
            )
            return self.get_merchandise(merchandise_id)
        except sqlite3.IntegrityError:
            raise ValueError(f"Merchandise with name {name} already exists")

    def get_merchandise(self, merchandise_id: int) -> Optional[Dict[str, Any]]:
        """Get merchandise by ID."""
        row = self.get_by_id(merchandise_id)
        return dict(row) if row else None

    def get_merchandise_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get merchandise by name."""
        query = f"SELECT * FROM {self.table_name} WHERE name = ? AND status = 'ACTIVE'"
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, (name,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving merchandise by name: {e}")
            raise

    def update_merchandise(self, merchandise_id: int, **fields) -> bool:
        """Update merchandise fields."""
        return self.update(merchandise_id, **fields)

    def update_quantity(self, merchandise_id: int, quantity: int) -> bool:
        """Update merchandise quantity."""
        return self.update_merchandise(merchandise_id, quantity=quantity)

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all active merchandise."""
        query = f"SELECT * FROM {self.table_name} WHERE status = 'ACTIVE' ORDER BY created_at DESC"
        try:
            rows = self.execute_query(query)
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving all merchandise: {e}")
            raise

    def get_recent_items(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently updated/created merchandise items."""
        query = f"""
            SELECT * FROM {self.table_name}
            WHERE status = 'ACTIVE'
            ORDER BY updated_at DESC
            LIMIT ?
        """
        try:
            rows = self.execute_query(query, (limit,))
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving recent merchandise: {e}")
            raise

    def delete(self, merchandise_id: int) -> bool:
        """Soft delete a merchandise by setting its status to INACTIVE."""
        try:
            return self.update(merchandise_id, status='INACTIVE')
        except sqlite3.Error as e:
            self.logger.error(f"Error deleting merchandise: {e}")
            raise

    def get_category_distribution(self) -> List[Dict[str, Any]]:
        """Return distribution of merchandise by category (count and total quantity)."""
        query = f"""
            SELECT 
                COALESCE(NULLIF(TRIM(category), ''), 'Sem Categoria') as category,
                COUNT(*) as items,
                SUM(COALESCE(quantity, 0)) as total_quantity
            FROM {self.table_name}
            WHERE status = 'ACTIVE'
            GROUP BY COALESCE(NULLIF(TRIM(category), ''), 'Sem Categoria')
            ORDER BY total_quantity DESC, items DESC
        """
        try:
            rows = self.execute_query(query)
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving category distribution: {e}")
            raise