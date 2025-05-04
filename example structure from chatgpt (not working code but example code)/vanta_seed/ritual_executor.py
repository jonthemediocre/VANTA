# === ritual_executor.py ===

"""
RitualExecutor
Handles execution and management of rituals.
"""

import yaml
import os

class RitualExecutor:
    def __init__(self, rituals_file_path):
        self.rituals_file = rituals_file_path or 'templates/rituals.yaml'
        self.rituals = {}
        print("RitualExecutor initialized.")

    def load(self):
        abs_path = os.path.abspath(self.rituals_file)
        print(f"RitualExecutor → Loading rituals from: {abs_path}")

        try:
            if not os.path.exists(abs_path):
                print(f"  ⚠️ Rituals file not found: {abs_path}. Using empty rituals.")
                self.rituals = {}
                return

            with open(abs_path, 'r') as f:
                self.rituals = yaml.safe_load(f) or {}
            print("  ✅ Loaded rituals.")
        except Exception as e:
            print(f"  ⚠️ Error loading rituals → {e}")
            self.rituals = {}

    def apply_rituals(self, user_input):
        """
        Apply ritual rules to the user input.
        """
        print("RitualExecutor → Applying rituals.")
        applied = []

        for name, ritual in self.rituals.items():
            trigger = ritual.get("trigger")
            response = ritual.get("response")

            if trigger and trigger.lower() in user_input.lower():
                applied.append(response)
                print(f"  Ritual '{name}' applied → {response}")

        return "\n".join(applied) if applied else None
