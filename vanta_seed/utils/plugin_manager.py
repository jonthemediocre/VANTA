# vanta_seed/utils/plugin_manager.py
import logging
import os
import importlib
import inspect # Needed to inspect classes
from pathlib import Path # Use Path for consistency
from typing import Type, Optional, List, Any, Dict

# --- Import BaseAgent for type checking --- #
# Assuming BaseAgent is correctly located relative to this file
try:
    from ..agents.base_agent import BaseAgent
except ImportError:
    # Handle cases where the structure might be different or run standalone
    BaseAgent = None
    logging.getLogger(__name__).warning("Could not import BaseAgent relative to PluginManager. Type checking might be limited.")

class PluginManager:
    """Manages discovery and loading of agent plugins (classes inheriting from BaseAgent)."""

    def __init__(self, plugin_directory: str):
        self.plugin_directory = Path(plugin_directory).resolve()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._loaded_plugins: Dict[str, Type[BaseAgent]] = {} # Store fully qualified name -> class type
        self.logger.info(f"PluginManager initialized for directory: {self.plugin_directory}")

    def load_plugins(self):
        """Scans the plugin directory, imports modules, and finds agent classes."""
        self.logger.info(f"Scanning for agent plugins in: {self.plugin_directory}")
        self._loaded_plugins = {}
        if not self.plugin_directory.is_dir():
            self.logger.error(f"Plugin directory not found or not a directory: {self.plugin_directory}")
            return

        # --- Determine the base package path for import --- 
        # Assumes plugin_directory is like '.../vanta_seed/agents'
        # We want the import base to be 'vanta_seed'
        # This is fragile; consider making this configurable or using package resources
        try:
            # Go up one level from 'agents' to get 'vanta_seed'
            base_package_name = self.plugin_directory.parent.name 
            self.logger.debug(f"Deduced base package name for imports: '{base_package_name}'")
        except IndexError:
            self.logger.error("Could not determine base package name from plugin directory path. Imports might fail.")
            base_package_name = ""

        for root, _, files in os.walk(self.plugin_directory):
            for filename in files:
                if filename.endswith('.py') and not filename.startswith('__'):
                    file_path = Path(root) / filename
                    # --- Construct module path relative to base package --- 
                    relative_path = file_path.relative_to(self.plugin_directory.parent)
                    # Convert path separators to dots, remove .py extension
                    module_name_parts = list(relative_path.parts)
                    module_name_parts[-1] = module_name_parts[-1][:-3] # Remove .py
                    # --- FIX: Prepend base package name --- 
                    if base_package_name:
                        # Construct path like vanta_seed.agents.echo_agent
                        module_path = f"{base_package_name}.{'.'.join(module_name_parts)}"
                    else:
                        # Fallback if base package couldn't be determined
                        module_path = '.'.join(module_name_parts)
                    # ------------------------------------------
                    
                    try:
                        self.logger.debug(f"Attempting to import module: {module_path}")
                        module = importlib.import_module(module_path)
                        for name, obj in inspect.getmembers(module):
                            # Ensure BaseAgent was imported successfully before using it
                            if inspect.isclass(obj) and BaseAgent and issubclass(obj, BaseAgent) and obj is not BaseAgent:
                                # Found an agent class
                                full_class_name = f"{module_path}.{name}"
                                if full_class_name in self._loaded_plugins:
                                    self.logger.warning(f"Plugin class '{full_class_name}' already loaded. Skipping duplicate.")
                                else:
                                    self.logger.info(f"Discovered agent plugin: '{full_class_name}'")
                                    self._loaded_plugins[full_class_name] = obj
                    except ImportError as e:
                        self.logger.error(f"Failed to import plugin module '{module_path}': {e}", exc_info=False) # Less noisy logging
                    except Exception as e:
                        self.logger.error(f"Error processing plugin file '{file_path}': {e}", exc_info=True)
        
        self.logger.info(f"Finished loading plugins. Total discovered: {len(self._loaded_plugins)}")

    def get_plugin_class(self, class_path: str, base_class: Optional[Type] = None) -> Optional[Type[Any]]:
        """Retrieves a loaded plugin class by its fully qualified name."""
        plugin_class = self._loaded_plugins.get(class_path)
        
        if plugin_class is None:
            self.logger.warning(f"Plugin class '{class_path}' not found in loaded plugins. Attempting dynamic load.")
            # --- Attempt dynamic load if not found (optional fallback) ---
            try:
                module_path, class_name = class_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                plugin_class = getattr(module, class_name, None)
                if plugin_class:
                     self.logger.info(f"Dynamically loaded plugin class: '{class_path}'")
                     # Optionally add it to the cache? 
                     # self._loaded_plugins[class_path] = plugin_class 
                else:
                     self.logger.error(f"Dynamic load failed: Class '{class_name}' not found in module '{module_path}'.")
                     return None
            except ImportError as e:
                self.logger.error(f"Dynamic load failed: Could not import module '{module_path}': {e}")
                return None
            except AttributeError:
                 self.logger.error(f"Dynamic load failed: Class '{class_name}' not found after importing '{module_path}'.")
                 return None
            except Exception as e:
                 self.logger.error(f"Dynamic load failed for '{class_path}': {e}", exc_info=True)
                 return None

        # --- Type Checking (if base_class provided and class loaded) --- 
        if plugin_class and base_class and not issubclass(plugin_class, base_class):
            self.logger.error(f"Loaded class '{class_path}' does not inherit from expected base class '{base_class.__name__}'.")
            return None
            
        return plugin_class

    def list_plugins(self) -> List[str]:
        """Returns a list of fully qualified class paths for loaded plugins."""
        return list(self._loaded_plugins.keys()) 