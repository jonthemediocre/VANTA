# === governance_engine.py ===

"""
GovernanceEngine
Handles policy enforcement and rule-based decision making.
"""

import yaml
import os

class GovernanceEngine:
    def __init__(self, governance_file_path):
        self.governance_file = governance_file_path or 'templates/governance.yaml'
        self.policies = {}
        print("GovernanceEngine initialized.")

    def load(self):
        abs_path = os.path.abspath(self.governance_file)
        print(f"GovernanceEngine → Loading governance rules from: {abs_path}")

        try:
            if not os.path.exists(abs_path):
                print(f"  ⚠️ Governance rules file not found: {abs_path}. Using empty policies.")
                self.policies = {}
                return

            with open(abs_path, 'r') as f:
                self.policies = yaml.safe_load(f) or {}
            print("  ✅ Loaded governance policies.")
        except Exception as e:
            print(f"  ⚠️ Error loading governance policies → {e}")
            self.policies = {}

    def evaluate(self, action_context):
        """
        Evaluate an action against the governance policies.
        """
        action = action_context.get("action")
        print(f"GovernanceEngine → Evaluating action: {action}")

        allowed_actions = self.policies.get("allowed_actions", [])
        blocked_actions = self.policies.get("blocked_actions", [])

        if action in blocked_actions:
            print(f"  🚫 Action '{action}' is blocked.")
            return False
        elif action in allowed_actions:
            print(f"  ✅ Action '{action}' is explicitly allowed.")
            return True
        else:
            print(f"  ⚠️ Action '{action}' is not explicitly covered. Defaulting to blocked.")
            return False
