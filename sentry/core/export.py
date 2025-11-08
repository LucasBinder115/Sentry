"""Utility functions for exporting data to CSV format."""

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class DataExporter:
    """Data export utility class."""
    
    def __init__(self, exports_dir: Path):
        """Initialize exporter with exports directory."""
        self.exports_dir = exports_dir
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        
    def export_to_csv(self, data: List[Dict[str, Any]], filename: str, headers: Dict[str, str]) -> Path:
        """Export data to CSV file.
        
        Args:
            data: List of dictionaries containing data to export
            filename: Base filename (without extension)
            headers: Dictionary mapping data keys to human-readable headers
            
        Returns:
            Path to the exported file
        """
        try:
            # Add timestamp to filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            full_filename = f"{filename}_{timestamp}.csv"
            filepath = self.exports_dir / full_filename
            
            # Write CSV file
            with filepath.open('w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write headers
                writer.writerow(headers.values())
                
                # Write data rows
                for row in data:
                    writer.writerow([str(row.get(key, '')) for key in headers.keys()])
                    
            logger.info(f"Exported data to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Export error: {e}")
            raise