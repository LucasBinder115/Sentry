"""Backup utility for database management."""

import os
import shutil
from datetime import datetime
import json
import logging
from typing import Optional, List, Dict

class BackupManager:
    """Manages database backups and restoration."""
    
    def __init__(self):
        """Initialize backup manager."""
        self.logger = logging.getLogger(__name__)
        self.backup_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'backups')
        self._ensure_backup_dir()
    
    def _ensure_backup_dir(self):
        """Ensure backup directory exists."""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            
    def create_backup(self, db_path: str, description: str = None) -> Optional[str]:
        """Create a new backup of the database."""
        try:
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}.db"
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # Copy database file
            shutil.copy2(db_path, backup_path)
            
            # Create metadata file
            metadata = {
                'timestamp': timestamp,
                'description': description,
                'original_path': db_path,
                'size': os.path.getsize(backup_path),
                'created_at': datetime.now().isoformat()
            }
            
            metadata_path = f"{backup_path}.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
                
            self.logger.info(f"Backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Error creating backup: {e}")
            return None
            
    def list_backups(self) -> List[Dict]:
        """List all available backups with their metadata."""
        backups = []
        try:
            for file in os.listdir(self.backup_dir):
                if file.endswith('.db'):
                    metadata_path = os.path.join(self.backup_dir, f"{file}.json")
                    if os.path.exists(metadata_path):
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                            backups.append({
                                'file': file,
                                **metadata
                            })
            
            return sorted(backups, key=lambda x: x['timestamp'], reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error listing backups: {e}")
            return []
            
    def restore_backup(self, backup_path: str, target_path: str = None) -> bool:
        """Restore a database from backup."""
        try:
            if not os.path.exists(backup_path):
                raise FileNotFoundError(f"Backup file not found: {backup_path}")
                
            # If target path not specified, use the original path from metadata
            if not target_path:
                metadata_path = f"{backup_path}.json"
                if os.path.exists(metadata_path):
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                        target_path = metadata.get('original_path')
                        
            if not target_path:
                raise ValueError("Target path not specified and not found in metadata")
                
            # Create a backup of current database before restoring
            current_backup = self.create_backup(
                target_path, 
                "Auto-backup before restore"
            )
            
            # Restore the backup
            shutil.copy2(backup_path, target_path)
            
            self.logger.info(
                f"Database restored from {backup_path} to {target_path}. "
                f"Previous version backed up to {current_backup}"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Error restoring backup: {e}")
            return False
            
    def delete_backup(self, backup_path: str) -> bool:
        """Delete a backup and its metadata."""
        try:
            if not os.path.exists(backup_path):
                return False
                
            # Delete backup file
            os.remove(backup_path)
            
            # Delete metadata if exists
            metadata_path = f"{backup_path}.json"
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
                
            self.logger.info(f"Backup deleted: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting backup: {e}")
            return False
            
    def cleanup_old_backups(self, max_backups: int = 10) -> bool:
        """Remove old backups keeping only the specified number of recent ones."""
        try:
            backups = self.list_backups()
            
            if len(backups) <= max_backups:
                return True
                
            # Delete oldest backups
            for backup in backups[max_backups:]:
                backup_path = os.path.join(self.backup_dir, backup['file'])
                self.delete_backup(backup_path)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old backups: {e}")
            return False