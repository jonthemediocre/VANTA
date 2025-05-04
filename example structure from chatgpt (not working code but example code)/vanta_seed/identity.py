# === identity.py ===

"""
Identity
Handles agentic identity, symbolic self-representation, and state.
"""

import yaml
import os

class Identity:
    def __init__(self, identity_file_path):
        self.identity_file = identity_file_path or 'templates/identity.yaml'
        self.identity_data = {}
        print("Identity initialized.")

    def load(self):
        abs_path = os.path.abspath(self.identity_file)
        print(f"Identity → Loading identity from: {abs_path}")

        try:
            if not os.path.exists(abs_path):
                print(f"  ⚠️ Identity file not found: {abs_path}. Using empty identity.")
                self.identity_data = {}
                return

            with open(abs_path, 'r') as f:
                self.identity_data = yaml.safe_load(f) or {}
            print("  ✅ Loaded identity definition.")
        except Exception as e:
            print(f"  ⚠️ Error loading identity → {e}")
            self.identity_data = {}

    def get_trait(self, key, default=None):
        """
        Retrieve a trait from the identity.
        """
        return self.identity_data.get("traits", {}).get(key, default)

    def describe_self(self):
        """
        Return a description of the identity.
        """
        return self.identity_data.get("description", "Unknown identity.")
