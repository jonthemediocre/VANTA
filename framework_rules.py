"""
Component for loading and managing VANTA Framework Runtime Rules.
"""
import os
import yaml
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FrameworkRuleEngine:
    """Loads and provides access to framework runtime rules."""

    def __init__(self, rule_index_path="FrAMEWORK RULES/rule-index.yaml"):
        """Initialize the engine with the path to the rule index YAML file."""
        self.rule_index_path = rule_index_path
        self.rules_dir = os.path.dirname(rule_index_path)
        self.loaded_rules = {}
        logger.info(f"FrameworkRuleEngine initialized with index: {self.rule_index_path}")

    def load_rules(self) -> dict:
        """Loads rules specified in the index file, handling errors gracefully.

        Returns:
            dict: A dictionary where keys are rule names and values are the
                  rule content (or parsed data if implemented).
        """
        try:
            with open(self.rule_index_path, 'r', encoding='utf-8') as f:
                index_data = yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Rule index file not found: {self.rule_index_path}")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing rule index file {self.rule_index_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error reading rule index {self.rule_index_path}: {e}")
            return {}

        if not index_data or 'rules' not in index_data:
            logger.warning(f"Rule index file {self.rule_index_path} is empty or missing 'rules' key.")
            return {}

        self.loaded_rules = {}
        for rule_entry in index_data.get('rules', []):
            rule_name = rule_entry.get('name')
            rule_file = rule_entry.get('file')

            if not rule_name or not rule_file:
                logger.warning(f"Skipping invalid rule entry in index: {rule_entry}")
                continue

            rule_file_path = os.path.join(self.rules_dir, rule_file)
            try:
                with open(rule_file_path, 'r', encoding='utf-8') as rf:
                    # For now, just load the raw content. Parsing could be added here.
                    # Example Parsing (if rules were simple key-value):
                    # parsed_rule = {} 
                    # for line in rf:
                    #    if ':' in line:
                    #       key, value = line.split(':', 1)
                    #       parsed_rule[key.strip()] = value.strip()
                    # self.loaded_rules[rule_name] = parsed_rule
                    
                    rule_content = rf.read()
                    self.loaded_rules[rule_name] = rule_content 
                    logger.info(f"Successfully loaded framework rule: {rule_name} from {rule_file}")

            except FileNotFoundError:
                logger.error(f"Framework rule file not found: {rule_file_path} (referenced by rule '{rule_name}')")
            except Exception as e:
                logger.error(f"Error reading framework rule file {rule_file_path} for rule '{rule_name}': {e}")

        logger.info(f"Finished loading framework rules. {len(self.loaded_rules)} rules loaded.")
        return self.loaded_rules

    def get_rule(self, rule_name: str) -> str | dict | None:
        """Get a specific loaded rule by name."""
        return self.loaded_rules.get(rule_name) 