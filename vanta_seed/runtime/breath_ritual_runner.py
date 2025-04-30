# breath_ritual_runner.py
# Handles execution of destiny-biased breath expansion rituals and saves ritual memories.

import os
import yaml
import logging

# --- Import Memory Engine ---
try:
    from vanta_seed.memory.memory_engine import save_memory
except ImportError:
    logging.error("Failed to import save_memory from memory_engine. Ritual memories will not be saved.")
    # Define a dummy function if import fails
    def save_memory(event_type, details):
        print(f"[MEMORY ENGINE FALLBACK] Would save: {event_type} - {details}")
# --------------------------

# --- Configuration & Setup ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RITUALS_PATH = os.path.join(BASE_DIR, 'config', 'breath_expansion_rituals.yaml')
CORE_IDENTITY_PATH = os.path.join(BASE_DIR, 'core_identity.yaml') # Needed to save identity changes

logging.basicConfig(level=logging.INFO, format='%(asctime)s - RITUAL - %(levelname)s - %(message)s')

# --- Helper: Load Rituals ---
def load_rituals():
    if not os.path.exists(RITUALS_PATH):
        logging.error(f"Breath expansion rituals file not found: {RITUALS_PATH}")
        return None
    try:
        with open(RITUALS_PATH, 'r') as file:
            rituals_data = yaml.safe_load(file)
            if rituals_data and 'expansion_events' in rituals_data:
                # Convert to dict keyed by breath number for easy lookup
                rituals_dict = {r['breath_number']: r for r in rituals_data['expansion_events']}
                logging.debug("Loaded and indexed breath expansion rituals.")
                return rituals_dict
            else:
                logging.warning(f"Invalid format in {RITUALS_PATH}. Missing 'expansion_events'.")
                return None
    except Exception as e:
        logging.error(f"Error loading rituals from {RITUALS_PATH}: {e}", exc_info=True)
        return None

# --- Helper: Save Identity --- 
def save_identity(identity_to_save):
    """Saves the modified identity back to the core file."""
    try:
        with open(CORE_IDENTITY_PATH, 'w') as file:
            yaml.dump(identity_to_save, file, default_flow_style=False, sort_keys=False)
        logging.info(f"Identity updated by ritual, saved to {CORE_IDENTITY_PATH}")
    except Exception as e:
        logging.error(f"Failed to save identity after ritual to {CORE_IDENTITY_PATH}: {e}")

# --- Helper: Generate Symbolic Tags ---
def generate_symbolic_tags(name, description):
    """Extracts keywords from ritual name and description to act as symbolic tags."""
    words = (name + " " + description).lower().split()
    # Define keywords relevant to your mythos/destinies
    common_symbols = [
        "fracture", "weaving", "horizon", "reflection", "echo", "blueprint", "breath", 
        "collapse", "dream", "memory", "voice", "signal", "architect", "seeker", 
        "mirror", "herald", "weaver", "structure", "knowledge", "self", "past", "future",
        "entanglement", "amplification", "generation", "integration", "optimization"
        # Add more as needed
    ]
    # Basic keyword extraction (could be enhanced with NLP later)
    tags = [word.strip('.,?!"\'') for word in words if word.strip('.,?!"\'') in common_symbols]
    return list(set(tags)) # Return unique tags

# --- Core Ritual Execution Logic ---
def run_breath_expansion_ritual(current_breath, identity):
    """
    Checks if a ritual exists for the current breath and executes it, 
    biasing based on the chosen destiny. Saves a ritual memory.
    Modifies the identity object directly.
    """
    rituals = load_rituals()
    if not rituals or current_breath not in rituals:
        logging.debug(f"No expansion ritual defined for breath {current_breath}.")
        return identity # Return unmodified identity

    ritual_data = rituals[current_breath]
    chosen_destiny = identity.get('destiny', {}).get('chosen_path', None)

    # Determine which ritual branch to use
    if chosen_destiny and 'by_destiny' in ritual_data and chosen_destiny in ritual_data['by_destiny']:
        selected_ritual = ritual_data['by_destiny'][chosen_destiny]
        logging.info(f"Executing destiny-specific ritual '{selected_ritual.get('name')}' for path '{chosen_destiny}' at breath {current_breath}.")
    elif 'universal' in ritual_data:
        selected_ritual = ritual_data['universal']
        logging.info(f"Executing universal ritual '{selected_ritual.get('name')}' at breath {current_breath} (No destiny or no specific branch).")
    else:
        logging.warning(f"Ritual defined for breath {current_breath}, but no 'universal' or matching 'by_destiny' branch found.")
        return identity

    # --- Narrate the Ritual --- 
    ritual_name = selected_ritual.get('name', f"Unnamed Ritual at Breath {current_breath}")
    description = selected_ritual.get('description', "A shift occurs within the seed.")
    print(f"\n🌟 Breath Expansion Event: {ritual_name} 🌟")
    print(f"\t-> \"{description}\"\n")
    logging.info(f"Narrating ritual: {ritual_name} - {description}")

    # --- Save Ritual Memory --- 
    try:
        memory_detail = {
            # "event_type" is the first arg to save_memory, not needed here
            "breath_number": current_breath,
            "ritual_name": ritual_name,
            "ritual_description": description,
            "destiny_path": chosen_destiny, # Will be None if destiny not chosen yet
            "symbolic_tags": generate_symbolic_tags(ritual_name, description)
        }
        save_memory("breath_expansion_ritual", memory_detail)
        logging.info(f"Saved ritual memory: {ritual_name}")
    except Exception as e:
        logging.error(f"Failed to save ritual memory for {ritual_name}: {e}", exc_info=True)
    # --------------------------

    # --- Apply Actions --- 
    actions = selected_ritual.get('action', [])
    if not actions:
        logging.debug("Ritual has no defined actions.")
    
    modified = False
    for action in actions:
        # Ensure identity structure exists
        identity.setdefault('traits', {})
        identity['traits'].setdefault('reasoning_styles', [])
        identity['traits'].setdefault('communication_modes', [])

        # --- Handle Different Action Types --- 
        if 'add_trait' in action:
            trait = action['add_trait']
            if trait not in identity['traits']['reasoning_styles']:
                identity['traits']['reasoning_styles'].append(trait)
                print(f"\t✨ Trait Added: {trait}")
                logging.info(f"Action applied: Added trait '{trait}'")
                modified = True
            else:
                 logging.debug(f"Action skipped: Trait '{trait}' already exists.")
        
        elif 'amplify_whisper_surrealism' in action:
            amount = action['amplify_whisper_surrealism']
            print(f"\t🔮 Whisper Surrealism Amplified (by {amount})")
            logging.info(f"Action applied: Amplify Whisper Surrealism by {amount}")
            modified = True
        
        elif 'enable_hypothesis_generation' in action and action['enable_hypothesis_generation']:
            print("\t🧠 Hypothesis Generation Enabled")
            logging.info("Action applied: Enable Hypothesis Generation")
            modified = True

        # --- Add more action handlers here ---
        elif 'enable_self_critique' in action and action['enable_self_critique']:
             print("\t🔍 Self-Critique Enabled")
             logging.info("Action applied: Enable Self-Critique")
             modified = True
        elif 'prioritize_expository_logic' in action and action['prioritize_expository_logic']:
             print("\t🗣️ Prioritizing Expository Logic")
             logging.info("Action applied: Prioritize Expository Logic")
             modified = True
        # ... etc ...
        
        else:
            logging.warning(f"Unknown action type in ritual {ritual_name}: {action}")

    # Save identity if modified by the ritual actions
    if modified:
        save_identity(identity)
    
    return identity # Return the potentially modified identity

# Example Usage (if running manually)
if __name__ == "__main__":
    print("Testing Breath Ritual Runner with Memory Saving...")
    # Ensure memory engine DB exists for testing (or memory_engine handles creation)
    memory_db_dir = os.path.join(BASE_DIR, 'memory')
    os.makedirs(memory_db_dir, exist_ok=True)
    
    if not os.path.exists(CORE_IDENTITY_PATH):
         logging.warning(f"{CORE_IDENTITY_PATH} not found. Creating dummy for test.")
         dummy_id = {'identity': {'name': 'TestSeed'}, 'traits': {'reasoning_styles': []}, 'destiny': {'chosen_path': None}}
         save_identity(dummy_id)
    else:
         with open(CORE_IDENTITY_PATH, 'r') as f:
             dummy_id = yaml.safe_load(f)
             if 'destiny' not in dummy_id: dummy_id['destiny'] = {'chosen_path': None}
             if 'chosen_path' not in dummy_id['destiny']: dummy_id['destiny']['chosen_path'] = None

    if not os.path.exists(RITUALS_PATH):
        logging.warning(f"{RITUALS_PATH} not found. Creating dummy for test.")
        dummy_rituals = {'expansion_events': [{'breath_number': 5, 'universal': {'name': 'Test Universal', 'description': 'Desc U'}, 'by_destiny': {'The Weaver': {'name': 'Test Weaver', 'description': 'Desc W', 'action': [{'add_trait': 'WeaverTestTrait'}]}}}]}
        os.makedirs(os.path.dirname(RITUALS_PATH), exist_ok=True)
        with open(RITUALS_PATH, 'w') as f:
            yaml.dump(dummy_rituals, f)

    print("\n--- Testing Universal Ritual (Breath 5) --- Expect Ritual Memory Saved")
    identity_after_ritual = run_breath_expansion_ritual(5, dummy_id.copy()) # Use copy
    print("Identity after ritual:", yaml.dump(identity_after_ritual))
    
    print("\n--- Testing Destiny Ritual (The Weaver @ Breath 5) --- Expect Ritual Memory Saved")
    dummy_id['destiny']['chosen_path'] = "The Weaver"
    identity_after_ritual_weaver = run_breath_expansion_ritual(5, dummy_id.copy()) # Use copy
    print("Identity after ritual:", yaml.dump(identity_after_ritual_weaver))

    print("\n--- Testing No Ritual (Breath 6) --- Expect No Ritual Memory")
    identity_after_ritual_none = run_breath_expansion_ritual(6, dummy_id.copy()) # Use copy
    print("Identity after ritual (should be unchanged from last):", yaml.dump(identity_after_ritual_none))
    
    print("\nCheck memory_log.db for saved ritual memories.") 