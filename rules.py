# rules.py - Implementation for RuleSmith

import yaml
from pathlib import Path

class RuleSmith:
    def __init__(self, config: dict, blueprint: dict):
        self.config = config
        self.blueprint = blueprint
        self.rule_file_paths = config.get('parameters', {}).get('rule_file_paths', [])
        self.active_rules = {}
        print(f"Initializing RuleSmith (ID: {config.get('agent_id')})...")
        self.load_rules()

    def load_rules(self):
        print("RuleSmith: Loading rules...")
        self.active_rules = {}
        # TODO: Implement logic to parse rule_index.yaml and potentially other linked rule files (.yaml or even .mdc for logic)
        # Example: Load index first
        index_path_str = next((p for p in self.rule_file_paths if 'rule-index.yaml' in p), None)
        if index_path_str:
            index_path = Path(index_path_str)
            if index_path.exists():
                try:
                    with open(index_path, 'r') as f:
                        index_data = yaml.safe_load(f)
                        # Store index data or use it to load other specifics
                        self.active_rules['index'] = index_data
                        print(f"  Loaded rule index from: {index_path}")
                except Exception as e:
                    print(f"ERROR: Failed to load rule index {index_path}: {e}")
            else:
                print(f"WARN: Rule index file not found: {index_path}")
        else:
            print("WARN: No rule-index.yaml path defined in config.")
            
        # TODO: Load override.yaml, mutation-policies.yaml etc. based on Codex/config
        print(f"RuleSmith loaded {len(self.active_rules.get('index', []))} rules from index (placeholder)." )

    def get_active_rules(self, context: dict = None):
        """Returns the currently active rules, potentially filtered by context."""
        # TODO: Implement context filtering if needed
        return self.active_rules

    def update_rule(self, rule_id: str, new_definition: dict):
        print(f"RuleSmith: Updating rule ID: {rule_id}")
        # TODO: Implement logic to modify loaded rules and potentially persist changes back to YAML files
        pass

# Example usage (if run directly for testing)
if __name__ == '__main__':
    print("Testing RuleSmith standalone...")
    try:
        # Ensure the rule directory exists for the test
        rule_dir = Path('FrAmEwOrK/rules')
        rule_dir.mkdir(parents=True, exist_ok=True)
        # Create dummy index for test if it doesn't exist
        dummy_index = rule_dir / 'rule-index.yaml'
        if not dummy_index.exists():
            dummy_index.write_text("- id: test_rule\n  description: Test rule entry")
            
        with open('FrAmEwOrK/agents/core/RuleSmith.yaml', 'r') as f:
            test_config = yaml.safe_load(f)
        with open('blueprint.yaml', 'r') as f:
            test_blueprint = yaml.safe_load(f)
            
        if test_config and test_blueprint:
            rulesmith = RuleSmith(test_config, test_blueprint)
            active = rulesmith.get_active_rules()
            print(f"Active rules loaded: {len(active.get('index', []))}")
        else:
            print("Failed to load necessary test configs.")
    except FileNotFoundError:
        print("Required config files not found for standalone test.")
    except Exception as e:
        print(f"Error during standalone test: {e}") 