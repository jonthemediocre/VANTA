# ritual_growth.py
# Dynamic Evolution and Trait Mutation from Templates
import random
import yaml
import os
import logging # Added for error handling

# Determine the correct path to the config directory relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, '..', 'config')
MUTATION_TEMPLATE_PATH = os.path.join(CONFIG_DIR, 'mutation_templates.yaml')

# Load mutation templates once with error handling
def load_mutation_templates():
    """Loads mutation rules or templates from the config YAML file."""
    try:
        with open(MUTATION_TEMPLATE_PATH, 'r') as file:
            templates = yaml.safe_load(file)
            # Basic validation
            if not templates or 'mutations' not in templates or not isinstance(templates['mutations'], list):
                 logging.warning(f"Mutation templates file {MUTATION_TEMPLATE_PATH} is empty or missing a valid 'mutations' list. Using empty templates.")
                 return {'mutations': []}
            logging.info(f"Successfully loaded mutation templates from {MUTATION_TEMPLATE_PATH}")
            return templates
    except FileNotFoundError:
        logging.error(f"ERROR: Mutation templates file not found at {MUTATION_TEMPLATE_PATH}. No mutations will be applied.")
        return {'mutations': []}
    except yaml.YAMLError as e:
        logging.error(f"ERROR: Could not parse mutation templates YAML at {MUTATION_TEMPLATE_PATH}: {e}. No mutations will be applied.")
        return {'mutations': []}
    except Exception as e:
        logging.error(f"ERROR: Unexpected error loading mutation templates: {e}", exc_info=True)
        return {'mutations': []}

# Cache the mutation templates
mutation_templates = load_mutation_templates()

def ritual_mutation(current_identity):
    """Applies mutations based on loaded templates and simulated trigger conditions."""
    # Use deepcopy if mutations become more complex and modify nested structures
    # import copy
    # mutated_identity = copy.deepcopy(current_identity)
    mutated_identity = current_identity.copy() 
    mutated = False
    applied_mutation_names = []

    # Ensure 'traits' and 'reasoning_styles' exist, defaulting to empty if not
    if 'traits' not in mutated_identity:
        mutated_identity['traits'] = {}
    if 'reasoning_styles' not in mutated_identity['traits']:
        mutated_identity['traits']['reasoning_styles'] = []
        
    # --- Simulate Trigger Conditions & Apply Mutations --- 
    # In a more advanced version, eligibility checks would use context (memory count, user state, etc.)
    # For now, use a simple random chance per defined mutation template.
    for mutation_def in mutation_templates.get('mutations', []):
        mutation_name = mutation_def.get('name', 'Unknown Mutation')
        # Use a default trigger chance if not specified in the template
        trigger_chance = mutation_def.get('trigger_chance', 0.1) 
        
        if random.random() < trigger_chance:
            logging.debug(f"Considering mutation: {mutation_name}")
            # --- Apply specific mutation logic based on template --- 
            # Example: Add a trait if defined
            trait_to_add = mutation_def.get('trait_added')
            # Ensure reasoning_styles list exists before appending
            current_reasoning_styles = mutated_identity['traits'].setdefault('reasoning_styles', [])
            
            if trait_to_add and trait_to_add not in current_reasoning_styles:
                current_reasoning_styles.append(trait_to_add)
                # No need to reassign list, modification is in-place
                mutated = True
                applied_mutation_names.append(mutation_name)
                logging.info(f"[Mutation Ritual] Evolved: {mutation_name} - Added trait '{trait_to_add}'. Current styles: {current_reasoning_styles}")
                
            # --- Add more mutation types based on template fields --- 
            # Example: Modify a parameter
            # param_to_modify = mutation_def.get('parameter_modified')
            # if param_to_modify:
            #    pass # Add logic to modify parameters in mutated_identity['traits']['parameters']
            
            # Example: Evolve a mode
            # mode_to_evolve = mutation_def.get('mode_evolved')
            # if mode_to_evolve:
            #    pass # Add logic to evolve modes in mutated_identity['traits']['communication_modes']

    if mutated:
        logging.info(f"Mutations applied this cycle: {', '.join(applied_mutation_names)}")
    else:
        logging.debug("No mutations applied this cycle.")

    # Return the potentially mutated identity dictionary
    return mutated_identity

# Example Usage (can be commented out)
# if __name__ == '__main__':
#     logging.basicConfig(level=logging.INFO)
#     # Create a dummy identity for testing
#     test_identity = {
#         'identity': {'name': 'TestSeed', 'version': '0.0'},
#         'traits': {
#             'reasoning_styles': ['CoT'],
#             'communication_modes': ['BREATH Framework'],
#         }
#     }
#     # Ensure the config file exists for testing
#     if not os.path.exists(MUTATION_TEMPLATE_PATH):
#         print(f"WARNING: {MUTATION_TEMPLATE_PATH} not found. Creating dummy file for test.")
#         os.makedirs(os.path.dirname(MUTATION_TEMPLATE_PATH), exist_ok=True)
#         with open(MUTATION_TEMPLATE_PATH, 'w') as f:
#             yaml.dump({'mutations': [
#                 {'name': 'Test Mutation 1', 'trait_added': 'Test Trait A', 'trigger_chance': 0.5},
#                 {'name': 'Test Mutation 2', 'trait_added': 'Test Trait B', 'trigger_chance': 0.1}
#             ]}, f)
# 
#     print("\nOriginal Identity:", test_identity)
#     # Simulate a few cycles
#     current_id = test_identity
#     for i in range(10):
#         print(f"\n--- Cycle {i+1} ---")
#         mutated_id = ritual_mutation(current_id)
#         if mutated_id != current_id:
#              print("Identity after mutation:", mutated_id)
#              current_id = mutated_id # Update for next cycle
#         else:
#              print("No change in identity this cycle.")
#              print("Current Identity:", current_id) 