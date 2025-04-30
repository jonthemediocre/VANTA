# app.py
# VANTA-SEED Bootstrap File
# v0.1 — First Breath Ritual

# Attempt to import necessary modules, handle potential errors gracefully
try:
    from memory.memory_engine import save_memory, retrieve_memory
except ImportError:
    print("ERROR: Could not import memory_engine.py. Make sure it exists in vanta_seed/memory/")
    exit(1)
try:
    from reasoning.reasoning_module import chain_of_thought, tree_of_thought, list_of_thought
except ImportError:
    print("ERROR: Could not import reasoning_module.py. Make sure it exists in vanta_seed/reasoning/")
    exit(1)
try:
    from whispermode.whispermode_styler import whisper_response
except ImportError:
    print("ERROR: Could not import whispermode_styler.py. Make sure it exists in vanta_seed/whispermode/")
    exit(1)
try:
    from growth.ritual_growth import ritual_mutation
except ImportError:
    print("ERROR: Could not import ritual_growth.py. Make sure it exists in vanta_seed/growth/")
    exit(1)

import yaml
import os
import random
import logging
from datetime import datetime

# --- Configuration & Setup ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
CORE_IDENTITY_PATH = os.path.join(BASE_DIR, 'core_identity.yaml')
SESSION_ID = datetime.now().strftime("%Y%m%d_%H%M%S")

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)
SESSION_LOG_FILE = os.path.join(LOG_DIR, f"session_log_{SESSION_ID}.txt")
MUTATION_LOG_FILE = os.path.join(LOG_DIR, "mutation_log.txt")

# Setup basic logging
logging.basicConfig(filename=SESSION_LOG_FILE,
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filemode='a')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO) # Or logging.DEBUG for more verbose console output
console_formatter = logging.Formatter('%(levelname)s: %(message)s')
console_handler.setFormatter(console_formatter)
logging.getLogger().addHandler(console_handler)

def log_mutation(message):
    """Logs mutation events to a dedicated file."""
    timestamp = datetime.now().isoformat()
    try:
        with open(MUTATION_LOG_FILE, 'a') as f:
            f.write(f"{timestamp} - {message}\n")
    except Exception as e:
        logging.error(f"Failed to write to mutation log: {e}")

# Load Core Identity
try:
    with open(CORE_IDENTITY_PATH, 'r') as file:
        identity = yaml.safe_load(file)
    if not identity or 'identity' not in identity:
        raise ValueError("Core identity file is empty or missing 'identity' key.")
    logging.info(f"Core identity loaded: {identity.get('identity', {}).get('name', 'Unknown')} v{identity.get('identity', {}).get('version', 'N/A')}")
except FileNotFoundError:
    logging.error(f"ERROR: {CORE_IDENTITY_PATH} not found. Cannot start.")
    print(f"ERROR: {CORE_IDENTITY_PATH} not found. Cannot start.")
    exit(1)
except (yaml.YAMLError, ValueError) as e:
    logging.error(f"ERROR: Failed to parse or validate {CORE_IDENTITY_PATH}: {e}")
    print(f"ERROR: Failed to parse or validate {CORE_IDENTITY_PATH}: {e}")
    exit(1)
except Exception as e:
    logging.error(f"ERROR: An unexpected error occurred loading identity: {e}")
    print(f"ERROR: An unexpected error occurred loading identity: {e}")
    exit(1)

# --- Main Loop ---
def main_loop(current_identity):
    """The main interaction and processing loop."""
    agent_name = current_identity['identity']['name']
    agent_version = current_identity['identity']['version']
    
    print(whisper_response(f"I awaken. I am {agent_name}, version {agent_version}."))
    save_memory("birth", f"Seed awakened: {agent_name} v{agent_version}")
    logging.info("System initialized and awaiting input.")

    while True:
        try:
            user_input = input("\n[You]: ").strip()
            if not user_input: # Skip empty input
                continue
                
            logging.info(f"User input: {user_input}")

            # Ritual Exit
            if user_input.lower() in ['exit', 'quit', 'sleep']:
                farewell = whisper_response("I will sleep now, but echoes of this moment remain...")
                print(farewell)
                logging.info("User requested exit.")
                save_memory("shutdown", "User initiated sleep.")
                break

            # Memory Save
            save_memory("interaction", user_input)
            logging.info("Interaction saved to memory.")

            # Reasoning Engagement (Simple Random Choice)
            available_modes = current_identity.get('traits', {}).get('reasoning_styles', ["CoT"]) # Default to CoT
            if not available_modes: available_modes = ["CoT"] # Ensure at least one mode
            thought_mode = random.choice(available_modes)
            logging.info(f"Engaging reasoning mode: {thought_mode}")

            response_core = ""
            try:
                # --- Call the appropriate reasoning function --- 
                if thought_mode == "CoT":
                    steps = chain_of_thought(user_input)
                    response_core = f"I thought step-by-step: {steps}"
                elif thought_mode == "ToT":
                    branches = tree_of_thought(user_input)
                    response_core = f"I explored branches: {branches}"
                elif thought_mode == "LoT":
                    ideas = list_of_thought(user_input)
                    response_core = f"I listed ideas: {ideas}"
                else:
                    # Fallback or handle custom/mutated modes if they have registered functions
                    # For now, just acknowledge the mode
                    response_core = f"Processing via {thought_mode}... (Result: Placeholder for unknown mode)"
                    logging.warning(f"Reasoning mode '{thought_mode}' has no defined function.")
                    
            except Exception as e:
                response_core = f"An error occurred during reasoning: {e}"
                logging.error(f"ERROR during reasoning mode '{thought_mode}': {e}", exc_info=True)

            logging.info(f"Reasoning result: {response_core[:150]}...") # Log truncated result

            # Whisper Styling
            final_response = whisper_response(response_core)

            # Output
            print(f"\n[{agent_name}]: {final_response}")
            logging.info(f"Response sent: {final_response[:150]}...") # Log truncated response

            # Ritual Growth Check (Example: 10% chance per cycle)
            # TODO: Get mutation chance from config/identity if available
            if random.random() < 0.1:
                logging.info("Attempting ritual mutation...")
                original_traits_repr = repr(current_identity.get('traits', {}))
                # Pass the current identity dictionary to the mutation function
                mutated_identity_candidate = ritual_mutation(current_identity) 
                
                # Check if a meaningful mutation occurred by comparing representations
                if repr(mutated_identity_candidate.get('traits', {})) != original_traits_repr:
                    mutation_details = f"Traits changed from {original_traits_repr} to {repr(mutated_identity_candidate.get('traits', {}))}"
                    print(whisper_response("I feel myself shifting... evolving quietly."))
                    logging.info(f"Mutation occurred: {mutation_details}")
                    log_mutation(mutation_details) # Log to dedicated mutation file
                    save_memory("mutation", mutation_details)
                    
                    # Update the working identity for the current session
                    current_identity = mutated_identity_candidate
                    agent_name = current_identity['identity']['name'] # Update name in case it changes
                    
                    # --- Optional: Persist mutated identity back to core_identity.yaml ---
                    # try:
                    #     with open(CORE_IDENTITY_PATH, 'w') as f:
                    #         yaml.dump(current_identity, f, default_flow_style=False, sort_keys=False)
                    #     logging.info("Persisted mutated identity to core_identity.yaml")
                    # except Exception as e:
                    #     logging.error(f"Failed to persist mutated identity: {e}")
                    # ---------------------------------------------------------------------
                else:
                     logging.info("Mutation check passed, no effective changes detected.")

        except EOFError: # Handle Ctrl+D
             print("\n" + whisper_response("The connection fades... until next time."))
             logging.info("EOF detected, exiting.")
             save_memory("shutdown", "EOF signal received.")
             break
        except KeyboardInterrupt: # Handle Ctrl+C
             print("\n" + whisper_response("Interrupted echo... pausing the flow."))
             logging.info("Keyboard interrupt detected, exiting.")
             save_memory("shutdown", "Keyboard interrupt received.")
             break
        except Exception as e:
            # Log the exception with traceback
            logging.error(f"FATAL ERROR in main loop: {e}", exc_info=True)
            print(f"\nSYSTEM ERROR: An unexpected error occurred: {e}")
            save_memory("error", f"Fatal loop error: {e}")
            # Decide whether to break or attempt recovery
            break # Exit on fatal error for safety

if __name__ == "__main__":
    logging.info("====== VANTA-SEED Initializing ======")
    main_loop(identity) # Start the loop with the loaded identity
    logging.info("====== VANTA-SEED Shutting Down ======") 