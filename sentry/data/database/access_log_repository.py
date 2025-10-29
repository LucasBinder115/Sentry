"""Access log repository implementation."""

import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from .base_repository import BaseRepository

class AccessLogRepository(BaseRepository):
    """Repository for access log operations."""

    def __init__(self):
        super().__init__('access_logs')

    def log_access(
        self, 
        vehicle_id: int, 
        access_type: str, 
        photo_path: Optional[str] = None,
        plate_text: Optional[str] = None,
        ocr_confidence: Optional[float] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Log a vehicle access event with optional OCR data."""
        try:
            log_id = self.create({
                'vehicle_id': vehicle_id,
                'type': access_type,
                'timestamp': datetime.now().isoformat(),
                'photo_path': str(photo_path) if photo_path else None,
                'plate_text': plate_text,
                'ocr_confidence': ocr_confidence,
                'notes': notes,
                'status': 'ACTIVE'
            })
            
            return self.get_log_entry(log_id)
        except sqlite3.Error as e:
            self.logger.error(f"Error logging access: {e}")
            raise

    def get_log_entry(self, log_id: int) -> Dict[str, Any]:
        """Get a specific log entry with vehicle details."""
        query = """
            SELECT 
                l.*, 
                v.plate, 
                v.model,
                v.status as vehicle_status
            FROM access_logs l
            LEFT JOIN vehicles v ON l.vehicle_id = v.id
            WHERE l.id = ?
        """
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, (log_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving log entry: {e}")
            raise
            
    def get_recent_with_vehicle(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent access logs with vehicle details."""
        query = """
            SELECT 
                l.*,
                v.plate,
                v.model,
                v.status as vehicle_status,
                v.color
            FROM access_logs l
            LEFT JOIN vehicles v ON l.vehicle_id = v.id
            ORDER BY l.timestamp DESC
            LIMIT ?
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving recent logs: {e}")
            raise
            
    def get_vehicle_logs(
        self, 
        vehicle_id: int, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent access logs for a specific vehicle."""
        query = """
            SELECT 
                l.*,
                v.plate,
                v.model,
                v.status as vehicle_status
            FROM access_logs l
            LEFT JOIN vehicles v ON l.vehicle_id = v.id
            WHERE l.vehicle_id = ?
            ORDER BY l.timestamp DESC
            LIMIT ?
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (vehicle_id, limit))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving vehicle logs: {e}")
            raise

    def get_recent_logs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent access logs with vehicle details."""
        query = """
            SELECT 
                l.*, v.plate, v.model
            FROM access_logs l
            LEFT JOIN vehicles v ON l.vehicle_id = v.id
            ORDER BY l.timestamp DESC
            LIMIT ?
        """
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving recent logs: {e}")
            raise