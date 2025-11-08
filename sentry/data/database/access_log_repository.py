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
            with self.db.get_connection() as conn:
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
            ORDER BY l.created_at DESC
            LIMIT ?
        """
        
        try:
            with self.db.get_connection() as conn:
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
            with self.db.get_connection() as conn:
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
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving recent logs: {e}")
            raise

    def get_latest_scan(self) -> Optional[Dict[str, Any]]:
        """Return the most recent OCR/access log with vehicle details."""
        query = """
            SELECT 
                l.*, v.plate, v.model
            FROM access_logs l
            LEFT JOIN vehicles v ON l.vehicle_id = v.id
            ORDER BY l.created_at DESC
            LIMIT 1
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving latest scan: {e}")
            raise

    def count_failed_attempts(self, since: Optional[str] = None) -> int:
        """Count UNAUTHORIZED attempts optionally since an ISO datetime string."""
        base = "SELECT COUNT(*) FROM access_logs WHERE status = 'UNAUTHORIZED'"
        params: tuple = ()
        if since:
            base += " AND created_at >= ?"
            params = (since,)
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(base, params)
                row = cursor.fetchone()
                return int(row[0]) if row else 0
        except sqlite3.Error as e:
            self.logger.error(f"Error counting failed attempts: {e}")
            raise

    def count_today_failed_attempts(self) -> int:
        """Count UNAUTHORIZED attempts for the current day."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM access_logs 
                    WHERE status = 'UNAUTHORIZED' 
                      AND DATE(created_at) = DATE('now','localtime')
                    """
                )
                row = cursor.fetchone()
                return int(row[0]) if row else 0
        except sqlite3.Error as e:
            self.logger.error(f"Error counting today's failed attempts: {e}")
            raise

    def get_failure_rate_minutes(self, minutes: int = 15) -> float:
        """Return UNAUTHORIZED / total in the last N minutes (0..1)."""
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT 
                        SUM(CASE WHEN status='UNAUTHORIZED' THEN 1 ELSE 0 END) AS unauth,
                        COUNT(*) AS total
                    FROM access_logs
                    WHERE created_at >= datetime('now', ?)
                    """,
                    (f'-{int(minutes)} minutes',)
                )
                row = cur.fetchone()
                unauth = int(row[0] or 0)
                total = int(row[1] or 0)
                if total <= 0:
                    return 0.0
                return float(unauth) / float(total)
        except sqlite3.Error as e:
            self.logger.error(f"Error computing failure rate: {e}")
            return 0.0

    def count_in_transit_heuristic(self, window_hours: int = 2) -> int:
        """Option B heuristic: distinct plates seen as AUTHORIZED within the last window_hours.
        This approximates 'in transit' without a shipments table.
        """
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT COUNT(DISTINCT COALESCE(v.plate, l.detected_plate))
                    FROM access_logs l
                    LEFT JOIN vehicles v ON v.id = l.vehicle_id
                    WHERE l.status='AUTHORIZED' AND l.created_at >= datetime('now', ?)
                    """,
                    (f'-{int(window_hours)} hours',)
                )
                row = cur.fetchone()
                return int(row[0] or 0)
        except sqlite3.Error as e:
            self.logger.error(f"Error computing in-transit heuristic: {e}")
            return 0

    def get_today_logs(self) -> List[Dict[str, Any]]:
        """Return today's access logs joined with vehicles, ordered newest first."""
        query = """
            SELECT l.*, v.plate, v.model
            FROM access_logs l
            LEFT JOIN vehicles v ON l.vehicle_id = v.id
            WHERE DATE(l.created_at) = DATE('now','localtime')
            ORDER BY l.created_at DESC
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving today's logs: {e}")
            raise

    # --- Analytics helpers ---
    def get_counts_by_day(self, start_iso: str, end_iso: str) -> List[Dict[str, Any]]:
        """Return daily counts of OCR scans between start and end (inclusive)."""
        query = """
            SELECT DATE(created_at) as day, COUNT(*) as total
            FROM access_logs
            WHERE created_at BETWEEN ? AND ?
            GROUP BY DATE(created_at)
            ORDER BY DATE(created_at)
        """
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(query, (start_iso, end_iso))
                return [dict(r) for r in cur.fetchall()]
        except sqlite3.Error as e:
            self.logger.error(f"Error counting scans by day: {e}")
            raise

    def get_top_vehicles(self, start_iso: str, end_iso: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Return most frequent vehicles seen in access logs in date range."""
        query = """
            SELECT COALESCE(v.plate, detected_plate) AS plate, COUNT(*) AS cnt
            FROM access_logs l
            LEFT JOIN vehicles v ON l.vehicle_id = v.id
            WHERE l.created_at BETWEEN ? AND ?
            GROUP BY COALESCE(v.plate, detected_plate)
            ORDER BY cnt DESC
            LIMIT ?
        """
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(query, (start_iso, end_iso, limit))
                return [dict(r) for r in cur.fetchall()]
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving top vehicles: {e}")
            raise

    def get_accuracy_stats(self, start_iso: str, end_iso: str) -> Dict[str, Any]:
        """Return counts of AUTHORIZED vs UNAUTHORIZED for accuracy percentage."""
        query = """
            SELECT status, COUNT(*) as cnt
            FROM access_logs
            WHERE created_at BETWEEN ? AND ?
            GROUP BY status
        """
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(query, (start_iso, end_iso))
                rows = {row[0]: row[1] for row in cur.fetchall()}
                total = sum(rows.values()) or 1
                authorized = rows.get('AUTHORIZED', 0)
                unauthorized = rows.get('UNAUTHORIZED', 0)
                return {
                    'authorized': authorized,
                    'unauthorized': unauthorized,
                    'total': total,
                    'accuracy_pct': round(authorized * 100.0 / total, 2)
                }
        except sqlite3.Error as e:
            self.logger.error(f"Error computing accuracy stats: {e}")
            raise

    # --- Intelligence helpers ---
    def is_duplicate_scan(self, plate: str, window_seconds: int = 60) -> bool:
        """Return True if the same plate was scanned within the last window_seconds."""
        if not plate:
            return False
        query = """
            SELECT COUNT(*) FROM access_logs
            WHERE detected_plate = ?
              AND created_at >= datetime('now', ?)
        """
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(query, (plate, f'-{int(window_seconds)} seconds'))
                row = cur.fetchone()
                return bool(row and int(row[0]) > 0)
        except sqlite3.Error as e:
            self.logger.error(f"Error checking duplicate scan: {e}")
            return False

    def quick_log_scan(self, plate: str, status: str = 'AUTHORIZED') -> bool:
        """Insert a minimal access log row (detected_plate/status)."""
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO access_logs (detected_plate, status, created_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    """,
                    (plate, status)
                )
                conn.commit()
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Error logging quick scan: {e}")
            return False

    # --- Session and activity logging ---
    def log_login(self, user_id: int, username: str) -> bool:
        """Record a LOGIN event into activity_logs."""
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO activity_logs (activity_type, description, entity_type, entity_id, user_id)
                    VALUES ('LOGIN', ?, 'user', ?, ?)
                    """,
                    (f'User {username} logged in', user_id, user_id)
                )
                conn.commit()
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Error logging login: {e}")
            return False

    def log_logout(self, user_id: int, username: str) -> bool:
        """Record a LOGOUT event into activity_logs."""
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO activity_logs (activity_type, description, entity_type, entity_id, user_id)
                    VALUES ('LOGOUT', ?, 'user', ?, ?)
                    """,
                    (f'User {username} logged out', user_id, user_id)
                )
                conn.commit()
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Error logging logout: {e}")
            return False

    def log_user_action(self, user_id: int, action: str, description: str, entity_type: str = 'system', entity_id: int = None) -> bool:
        """Record an arbitrary user action into activity_logs."""
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO activity_logs (activity_type, description, entity_type, entity_id, user_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (action.upper(), description, entity_type, entity_id, user_id)
                )
                conn.commit()
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Error logging user action: {e}")
            return False

    def get_recent_session_logs(self, limit: int = 50):
        """Fetch recent LOGIN/LOGOUT activities."""
        query = (
            "SELECT * FROM activity_logs WHERE activity_type IN ('LOGIN','LOGOUT') "
            "ORDER BY created_at DESC LIMIT ?"
        )
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(query, (limit,))
                rows = cur.fetchall()
                return [dict(r) for r in rows]
        except sqlite3.Error as e:
            self.logger.error(f"Error fetching session logs: {e}")
            return []

    # --- Carrier analytics ---
    def get_top_carriers(self, start_iso: str, end_iso: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Return carriers with most trips in date range (by access_logs.carrier_id)."""
        query = """
            SELECT c.name AS carrier, COUNT(*) AS cnt
            FROM access_logs l
            JOIN carriers c ON c.id = l.carrier_id
            WHERE l.created_at BETWEEN ? AND ?
            GROUP BY c.id, c.name
            ORDER BY cnt DESC
            LIMIT ?
        """
        try:
            with self.db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(query, (start_iso, end_iso, limit))
                return [dict(r) for r in cur.fetchall()]
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving top carriers: {e}")
            raise