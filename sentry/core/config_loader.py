from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict

try:
    import yaml  # type: ignore
    _HAS_YAML = True
except Exception:
    yaml = None
    _HAS_YAML = False


class ConfigLoader:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    def load(self) -> Dict[str, Any]:
        """Load config overrides from config.yaml or config.json if present."""
        # Prefer YAML if available
        yaml_path = self.base_dir / "config.yaml"
        json_path = self.base_dir / "config.json"
        if yaml_path.exists() and _HAS_YAML:
            try:
                with yaml_path.open("r", encoding="utf-8") as f:  # type: ignore
                    data = yaml.safe_load(f) or {}
                    if isinstance(data, dict):
                        return data
            except Exception:
                return {}
        if json_path.exists():
            try:
                with json_path.open("r", encoding="utf-8") as f:
                    data = json.load(f) or {}
                    if isinstance(data, dict):
                        return data
            except Exception:
                return {}
        return {}
