"""Carrier repository for database operations."""

import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base_repository import BaseRepository

class CarrierRepository(BaseRepository):
    """Repository for carrier-related database operations."""

    def __init__(self):
        """Initialize carrier repository."""
        super().__init__('carriers')

    def create_carrier(self, name: str, cnpj: str, contact_phone: str = None) -> Dict[str, Any]:
        """Create a new carrier record."""
        try:
            # Format CNPJ to standard format
            cnpj = ''.join(filter(str.isdigit, cnpj))
            if len(cnpj) != 14:
                raise ValueError("CNPJ must have 14 digits")

            carrier_id = self.create(
                name=name,
                cnpj=cnpj,
                contact_phone=contact_phone,
                status='ACTIVE'
            )
            
            return self.get_carrier(carrier_id)
        except sqlite3.IntegrityError:
            raise ValueError(f"Carrier with CNPJ {cnpj} already exists")

    def get_carrier(self, carrier_id: int) -> Optional[Dict[str, Any]]:
        """Get carrier by ID."""
        row = self.get_by_id(carrier_id)
        return dict(row) if row else None

    def get_carrier_by_cnpj(self, cnpj: str) -> Optional[Dict[str, Any]]:
        """Get carrier by CNPJ."""
        cnpj = ''.join(filter(str.isdigit, cnpj))
        query = f"SELECT * FROM {self.table_name} WHERE cnpj = ? AND status = 'ACTIVE'"
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, (cnpj,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving carrier by CNPJ: {e}")
            raise

    def update_carrier(self, carrier_id: int, **fields) -> bool:
        """Update carrier fields."""
        if 'cnpj' in fields:
            fields['cnpj'] = ''.join(filter(str.isdigit, fields['cnpj']))
            if len(fields['cnpj']) != 14:
                raise ValueError("CNPJ must have 14 digits")
        return self.update(carrier_id, **fields)

    def get_recent_carriers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently added carriers."""
        query = f"""
            SELECT * FROM {self.table_name} 
            WHERE status = 'ACTIVE'
            ORDER BY created_at DESC 
            LIMIT ?
        """
        
        try:
            rows = self.execute_query(query, (limit,))
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving recent carriers: {e}")
            raise