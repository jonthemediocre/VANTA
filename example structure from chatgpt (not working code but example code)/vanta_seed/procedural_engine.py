# === procedural_engine.py ===

"""
ProceduralEngine
Handles rule-based and template-driven procedural logic.
"""

import yaml
import os

class ProceduralEngine:
    def __init__(self, procedural_file_path):
        self.procedural_file = procedural_file_path or 'templates/procedural.yaml'
        self.procedures = {}
        print("ProceduralEngine initialized.")

    def load(self):
        abs_path = os.path.abspath(self.procedural_file)
        print(f"ProceduralEngine → Loading procedures from: {abs_path}")

        try:
            if not os.path.exists(abs_path):
                print(f"  ⚠️ Procedures file not found: {abs_path}. Using empty procedures.")
                self.procedures = {}
                return

            with open(abs_path, 'r') as f:
                self.procedures = yaml.safe_load(f) or {}
            print("  ✅ Loaded procedural logic.")
        except Exception as e:
            print(f"  ⚠️ Error loading procedures → {e}")
            self.procedures = {}

    def get_procedure(self, name):
        """
        Get a procedure definition.
        """
        return self.procedures.get(name)

    def execute_procedure(self, name, context=None):
        """
        Execute a procedural step (placeholder implementation).
        """
        proc = self.get_procedure(name)

        if not proc:
            print(f"ProceduralEngine → No procedure found for: {name}")
            return None

        print(f"ProceduralEngine → Executing procedure: {name}")

        # Placeholder execution logic
        result = {"status": "executed", "procedure": name, "details": proc}
        return result
