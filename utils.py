"""
VANTA Kernel - Utility Functions

This module provides common utility functions for loading configuration data,
registry files, and potentially other shared resources used across different scripts
and modules within the VANTA ecosystem.
"""

import importlib.util
import sys
import os
import logging
import yaml
import json # Or pandas if CSV/structured data becomes complex

# Configure basic logging for utilities
logging.basicConfig(level=logging.INFO, format='%(asctime)s - UTILS - %(levelname)s - %(message)s')

# Define file paths relative to the project root
TRIGGER_REGISTRY_PATH = "trigger_registry.py"
ROLES_PATHS = ["roles.yaml", "caregiver_roles.yaml"]
EFFICACY_DATA_PATH_PLACEHOLDER = "data/efficacy_scores.jsonl" # Example path

def load_trigger_registry() -> list | None:
    """Safely loads the TriggerRegistry list from trigger_registry.py."""
    if not os.path.exists(TRIGGER_REGISTRY_PATH):
        logging.error(f"Trigger registry file not found: {TRIGGER_REGISTRY_PATH}")
        return None
    try:
        # Ensure the module can be found relative to the project root
        module_name = "trigger_registry"
        spec = importlib.util.spec_from_file_location(module_name, TRIGGER_REGISTRY_PATH)
        if spec is None:
             logging.error(f"Could not create module spec for {TRIGGER_REGISTRY_PATH}")
             return None
        trigger_mod = importlib.util.module_from_spec(spec)
        # Add module to sys.modules BEFORE executing it, helps with relative imports if any
        sys.modules[module_name] = trigger_mod 
        spec.loader.exec_module(trigger_mod)
        
        registry = getattr(trigger_mod, "TriggerRegistry", None)
        if registry is None:
            logging.error(f"'TriggerRegistry' list not found in {TRIGGER_REGISTRY_PATH}.")
            return None
        if not isinstance(registry, list):
            logging.error(f"'TriggerRegistry' in {TRIGGER_REGISTRY_PATH} is not a list.")
            return None
        logging.info(f"Successfully loaded {len(registry)} triggers from {TRIGGER_REGISTRY_PATH}.")
        return registry
    except Exception as e:
        logging.exception(f"Failed to load or parse {TRIGGER_REGISTRY_PATH}: {e}", exc_info=True)
        return None

def load_caregiver_roles() -> dict | None:
    """Loads caregiver roles from the first existing file in ROLES_PATHS."""
    loaded_path = None
    for path in ROLES_PATHS:
        if os.path.exists(path):
            loaded_path = path
            break
            
    if not loaded_path:
        logging.warning(f"No roles file found at expected paths: {ROLES_PATHS}")
        return None # Return None instead of {} to distinguish missing file from empty file
        
    try:
        with open(loaded_path, "r", encoding='utf-8') as f:
            roles = yaml.safe_load(f)
            if roles is None: # File exists but is empty
                 logging.warning(f"Roles file found at {loaded_path} but it is empty.")
                 return {}
            if not isinstance(roles, dict):
                logging.error(f"Roles file {loaded_path} does not contain a valid dictionary (YAML mapping).")
                return None
            logging.info(f"Successfully loaded {len(roles)} roles from {loaded_path}.")
            return roles
    except yaml.YAMLError as e:
        logging.exception(f"Error parsing YAML file {loaded_path}: {e}", exc_info=True)
        return None
    except IOError as e:
        logging.exception(f"Error reading roles file {loaded_path}: {e}", exc_info=True)
        return None
    except Exception as e:
        logging.exception(f"An unexpected error occurred loading roles from {loaded_path}: {e}", exc_info=True)
        return None

def load_efficacy_data() -> list | None:
    """
    Placeholder function to load efficacy data.
    In a real implementation, this might load from a database, a file (CSV, JSONL),
    or an API.
    Returns a list of efficacy records (e.g., list of dicts).
    """
    logging.info(f"Attempting to load efficacy data (placeholder). Path: {EFFICACY_DATA_PATH_PLACEHOLDER}")
    # Placeholder: Check if a dummy file exists and load it
    if os.path.exists(EFFICACY_DATA_PATH_PLACEHOLDER):
        try:
            data = []
            with open(EFFICACY_DATA_PATH_PLACEHOLDER, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data.append(json.loads(line))
                    except json.JSONDecodeError:
                        logging.warning(f"Skipping invalid JSON line in {EFFICACY_DATA_PATH_PLACEHOLDER}: {line.strip()}")
            logging.info(f"Loaded {len(data)} efficacy records from {EFFICACY_DATA_PATH_PLACEHOLDER}.")
            return data
        except IOError as e:
            logging.error(f"Failed to read efficacy data file {EFFICACY_DATA_PATH_PLACEHOLDER}: {e}")
            return None
        except Exception as e:
             logging.exception(f"An unexpected error occurred loading efficacy data: {e}", exc_info=True)
             return None
    else:
        logging.warning(f"Efficacy data file not found at {EFFICACY_DATA_PATH_PLACEHOLDER}. Returning empty list.")
        return [] # Return empty list if file doesn't exist for now

# Example of how to use the loaders (optional)
if __name__ == "__main__":
    print("Testing VANTA Utility Loaders...")
    
    print("\n--- Loading Trigger Registry ---")
    registry = load_trigger_registry()
    if registry is not None:
        print(f"Loaded {len(registry)} triggers.")
    else:
        print("Failed to load registry.")
        
    print("\n--- Loading Caregiver Roles ---")
    roles = load_caregiver_roles()
    if roles is not None:
        print(f"Loaded roles: {list(roles.keys())}")
    else:
        print("Failed to load roles or file not found.")
        
    print("\n--- Loading Efficacy Data (Placeholder) ---")
    efficacy_data = load_efficacy_data()
    if efficacy_data is not None:
        print(f"Loaded {len(efficacy_data)} efficacy records (placeholder).")
    else:
        print("Failed to load efficacy data (placeholder).") 