# === plugins.py ===

"""
Plugins
Handles plugin loading, registration, and execution.
"""

class Plugins:
    def __init__(self, config):
        self.config = config
        self.registry = {}
        print("Plugins initialized.")

    def register(self, name, plugin_instance):
        """
        Register a plugin instance.
        """
        print(f"Plugins → Registering plugin → {name}")
        self.registry[name] = plugin_instance

    def get(self, name):
        """
        Retrieve a plugin by name.
        """
        return self.registry.get(name)

    def list_plugins(self):
        """
        List all registered plugins.
        """
        return list(self.registry.keys())

    def execute_plugin(self, name, *args, **kwargs):
        """
        Execute a plugin's main method.
        """
        plugin = self.get(name)
        if plugin and hasattr(plugin, "run"):
            print(f"Plugins → Executing plugin → {name}")
            return plugin.run(*args, **kwargs)
        else:
            print(f"Plugins → Plugin '{name}' not found or missing run() method.")
            return None
