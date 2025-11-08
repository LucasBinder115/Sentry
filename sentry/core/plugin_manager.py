import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .event_bus import get_event_bus


class PluginContext:
    def __init__(self):
        self.events = get_event_bus()


class PluginManager:
    """Discovery and loading of plugins from a directory.

    A plugin is a folder with a Python file exposing an `init_plugin(context)` function.
    """

    def __init__(self, plugins_dir: Path):
        self.plugins_dir = plugins_dir
        self.context = PluginContext()
        self._loaded: Dict[str, Any] = {}

    def discover(self):
        if not self.plugins_dir.exists():
            return []
        return [p for p in self.plugins_dir.iterdir() if p.is_dir()]

    def load_all(self):
        for p in self.discover():
            self.load(p.name)

    def load(self, plugin_name: str) -> Optional[Any]:
        try:
            plugin_path = self.plugins_dir / plugin_name / "__init__.py"
            if not plugin_path.exists():
                # try main.py
                plugin_path = self.plugins_dir / plugin_name / "main.py"
                if not plugin_path.exists():
                    return None
            spec = importlib.util.spec_from_file_location(f"sentry_plugin_{plugin_name}", str(plugin_path))
            if not spec or not spec.loader:
                return None
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)  # type: ignore
            if hasattr(module, "init_plugin"):
                module.init_plugin(self.context)
            self._loaded[plugin_name] = module
            return module
        except Exception:
            return None

    def get(self, plugin_name: str) -> Optional[Any]:
        return self._loaded.get(plugin_name)
