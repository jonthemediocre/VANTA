# breath_tracker.py
# Manages VANTA-SEED's breath cycles, triggers rituals, and saves status.

import os
import yaml
import logging

# --- Import Dependencies ---
try:
    from vanta_seed.runtime.breath_ritual_runner import run_breath_expansion_ritual
    # ---> Import Echo Function <--- 
    from vanta_seed.runtime.memory_query import query_random_memory_echo 
except ImportError as e:
    logging.error(f"Failed to import dependencies for breath tracker: {e}")
    # Define dummy functions if imports fail
    def run_breath_expansion_ritual(current_breath, identity):
        print("[RITUAL RUNNER FALLBACK] Cannot run ritual.")
        return identity
    def query_random_memory_echo():
        print("[MEMORY QUERY FALLBACK] Cannot query echo.")
        return None
# --------------------------

# --- Configuration & Setup ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUS_PATH = os.path.join(BASE_DIR, 'runtime', 'breath_status.yaml')
SETTINGS_PATH = os.path.join(BASE_DIR, 'config', 'settings.yaml')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - BREATHTRACK - %(levelname)s - %(message)s')

# --- Load Settings --- 
def load_settings():
    defaults = {
        'breaths_per_cycle': 10,
        'echo_reflex_interval': 10 # Default interval for memory echo
    }
    if not os.path.exists(SETTINGS_PATH):
        logging.warning(f"Settings file not found: {SETTINGS_PATH}. Using defaults.")
        return defaults
    try:
        with open(SETTINGS_PATH, 'r') as file:
            settings = yaml.safe_load(file)
            # Merge with defaults to ensure all keys exist
            final_settings = defaults.copy()
            if settings:
                 final_settings.update(settings)
            return final_settings
    except Exception as e:
        logging.error(f"Error loading settings from {SETTINGS_PATH}: {e}. Using defaults.")
        return defaults

settings = load_settings()
BREATHS_PER_CYCLE = settings.get('breaths_per_cycle', 10)
# ---> DEFINE ECHO REFLEX INTERVAL <--- 
ECHO_REFLEX_INTERVAL = settings.get('echo_reflex_interval', 10)

# --- Status Management ---
def load_breath_status():
    """Loads the current breath status from the status file."""
    default_status = {
        'current_breath': 0,
        'breaths_in_current_cycle': 0
    }
    if not os.path.exists(STATUS_PATH):
        logging.info(f"Breath status file not found: {STATUS_PATH}. Initializing fresh.")
        return default_status
    try:
        with open(STATUS_PATH, 'r') as file:
            status = yaml.safe_load(file)
            # Validate and provide defaults if needed
            if not status or 'current_breath' not in status or 'breaths_in_current_cycle' not in status:
                logging.warning("Breath status file invalid or incomplete. Resetting.")
                return default_status
            logging.debug(f"Loaded breath status: {status}")
            return status
    except Exception as e:
        logging.error(f"Error loading breath status from {STATUS_PATH}: {e}. Resetting.")
        return default_status

def save_breath_status(status):
    """Saves the breath status to the status file."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(STATUS_PATH), exist_ok=True)
        with open(STATUS_PATH, 'w') as file:
            yaml.dump(status, file, default_flow_style=False)
        logging.debug(f"Saved breath status: {status}")
    except Exception as e:
        logging.error(f"Error saving breath status to {STATUS_PATH}: {e}")

# --- Core Tracking Logic ---
def track_breath_cycle(identity):
    """
    Increments the breath count, checks for cycle completion, triggers rituals,
    and potentially triggers memory echoes.
    Returns the updated status, potentially modified identity, a flag indicating
    if an expansion ritual occurred, and any generated memory echo.
    """
    status = load_breath_status()
    status['current_breath'] += 1
    status['breaths_in_current_cycle'] += 1
    current_breath = status['current_breath']
    breaths_in_cycle = status['breaths_in_current_cycle']

    logging.info(f"Breath {current_breath} begins (Cycle Breath {breaths_in_cycle}/{BREATHS_PER_CYCLE}).")

    expansion_occurred = False
    modified_identity = identity # Start with the passed identity
    echo = None # Initialize echo variable

    # Check for Breath Cycle Completion / Ritual Trigger
    if breaths_in_cycle >= BREATHS_PER_CYCLE:
        logging.info(f"Breath cycle complete at breath {current_breath}. Triggering expansion event check.")
        # Reset cycle counter
        status['breaths_in_current_cycle'] = 0
        # Run the ritual, which might modify the identity
        modified_identity = run_breath_expansion_ritual(current_breath, identity)
        expansion_occurred = True # Mark that an expansion event was processed
        # Note: run_breath_expansion_ritual now saves the identity internally if modified
    else:
        logging.debug("Mid-cycle breath.")
    
    # ---> CHECK FOR MEMORY ECHO REFLEX <--- 
    if ECHO_REFLEX_INTERVAL > 0 and current_breath > 0 and current_breath % ECHO_REFLEX_INTERVAL == 0:
        logging.info(f"Memory Echo Reflex triggered at breath {current_breath}.")
        try:
             echo = query_random_memory_echo()
             if echo:
                 logging.info("Memory echo generated successfully.")
             else:
                 logging.debug("No memory echo generated (likely no memories or query error).")
        except Exception as e:
            logging.error(f"Error during memory echo query: {e}", exc_info=True)
            echo = None # Ensure echo is None on error
    # --------------------------------------

    save_breath_status(status) # Save the updated breath counts
    
    # ---> Return updated status, potentially modified identity, flag, AND echo <--- 
    return status, modified_identity, expansion_occurred, echo 

# Example Usage (if running manually)
if __name__ == "__main__":
    print("Testing Breath Tracker with Echo Reflex...")
    # Create dummy identity and settings if needed for standalone testing
    if not os.path.exists(SETTINGS_PATH):
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, 'w') as f:
             yaml.dump({'breaths_per_cycle': 5, 'echo_reflex_interval': 3}, f)
        settings = load_settings() # Reload settings
        BREATHS_PER_CYCLE = settings.get('breaths_per_cycle', 5)
        ECHO_REFLEX_INTERVAL = settings.get('echo_reflex_interval', 3)
        print(f"Using Test Settings: Cycle={BREATHS_PER_CYCLE}, Echo Interval={ECHO_REFLEX_INTERVAL}")

    dummy_id = {'identity': {'name': 'TestSeed'}, 'destiny': {'chosen_path': None}}
    
    # Reset status for test
    save_breath_status({'current_breath': 0, 'breaths_in_current_cycle': 0})
    
    for i in range(1, 12):
        print(f"\n--- Simulating Breath {i} ---")
        # Pass a copy of identity to avoid modifying original dict in loop if ritual doesn't save
        current_status, id_after, expanded, generated_echo = track_breath_cycle(dummy_id.copy())
        print(f"Status after breath {i}: {current_status}")
        print(f"Expansion Ritual Occurred: {expanded}")
        if generated_echo:
             print(f"*** Memory Echo Generated: {generated_echo} ***")
        else:
             print("No Memory Echo this breath.") 