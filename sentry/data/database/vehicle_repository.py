"""Vehicle repository for database operations."""

import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base_repository import BaseRepository

class VehicleRepository(BaseRepository):
    """Repository for vehicle-related database operations."""

    def __init__(self):
        """Initialize vehicle repository."""
        super().__init__('vehicles')

    def create_vehicle(self, plate: str, model: str, color: str = None) -> Dict[str, Any]:
        """Create a new vehicle record."""
        try:
            vehicle_id = self.create(
                plate=plate.upper(),
                model=model,
                color=color,
                status='ACTIVE'
            )
            
            return self.get_vehicle(vehicle_id)
        except sqlite3.IntegrityError:
            raise ValueError(f"Vehicle with plate {plate} already exists")

    def get_vehicle(self, vehicle_id: int) -> Optional[Dict[str, Any]]:
        """Get vehicle by ID."""
        row = self.get_by_id(vehicle_id)
        return dict(row) if row else None

    def get_vehicle_by_plate(self, plate: str) -> Optional[Dict[str, Any]]:
        """Get vehicle by plate number."""
        query = f"SELECT * FROM {self.table_name} WHERE plate = ? AND status = 'ACTIVE'"
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, (plate.upper(),))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving vehicle by plate: {e}")
            raise

    def update_vehicle(self, vehicle_id: int, **fields) -> bool:
        """Update vehicle fields."""
        if 'plate' in fields:
            fields['plate'] = fields['plate'].upper()
        return self.update(vehicle_id, **fields)

    def get_recent_vehicles(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently added vehicles."""
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
            self.logger.error(f"Error retrieving recent vehicles: {e}")
            raise