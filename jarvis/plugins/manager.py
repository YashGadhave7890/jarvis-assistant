import importlib
import logging
import os
import sys
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PluginManager:
    """
    Loads and manages external plugins dynamically.
    Ensures plugins follow the standardized interfaces and communicate via the Event Bus.
    """
    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins_dir = plugins_dir
        self.loaded_plugins: Dict[str, Any] = {}
        
        # Add plugins directory to sys.path so we can import from it dynamically
        full_path = os.path.abspath(self.plugins_dir)
        if full_path not in sys.path:
            sys.path.append(full_path)

    def discover_and_load(self):
        """Scans the plugins directory and loads valid Python modules."""
        logger.info(f"Scanning for plugins in '{self.plugins_dir}'...")
        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir, exist_ok=True)
            return

        for item in os.listdir(self.plugins_dir):
            if item.endswith(".py") and not item.startswith("__") and item != "manager.py":
                module_name = item[:-3]
                self._load_plugin(module_name)

    def _load_plugin(self, module_name: str):
        try:
            module = importlib.import_module(module_name)
            # A valid plugin must have a setup() function
            if hasattr(module, "setup"):
                logger.info(f"Initializing plugin '{module_name}'...")
                # Typically we pass the event_bus to the plugin here
                # module.setup(event_bus)
                self.loaded_plugins[module_name] = module
            else:
                logger.warning(f"Plugin '{module_name}' missing setup() function. Skipping.")
        except Exception as e:
            logger.error(f"Failed to load plugin '{module_name}': {e}", exc_info=True)
