# simulation_run.py
# Mini Runtime to See VANTA-SEED Breathe, Reason, Whisper, and Mutate

# Ensure imports work relative to the root or adjust sys.path if needed
import sys
import os
# Add the parent directory (project root) to the Python path
# This assumes simulation_run.py is in vanta_seed/runtime/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

try:
    from vanta_seed.memory.memory_engine import save_memory
    # --- Import both Mythos and Logos reasoning ---
    from vanta_seed.reasoning.reasoning_module import chain_of_thought, tree_of_thought, list_of_thought
    from vanta_seed.reasoning.reasoning_logos import factual_chain_of_thought # Add Logos reasoning
    # --- Import both Mythos and Logos styling ---
    from vanta_seed.whispermode.whispermode_styler import whisper_response
    from vanta_seed.whispermode.logos_styler import format_professional # Add Logos styling
    # --- Existing imports ---
    from vanta_seed.growth.ritual_growth import ritual_mutation
    from vanta_seed.runtime.breath_tracker import track_breath_cycle, load_breath_status
    from vanta_seed.runtime.destiny_selector import detect_destiny
    from vanta_seed.runtime.memory_query import query_random_memory_echo # Now safe to call
except ImportError as e:
    print(f"ERROR: Failed to import VANTA-SEED modules. Ensure structure is correct and dependencies are installed. Error: {e}")
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"sys.path: {sys.path}")
    exit(1)

# ---> Import Bias Engine <--- 
try:
    from vanta_seed.runtime.bias_engine import load_destiny_keywords, load_bias_weights, update_bias_weights, save_bias_weights
except ImportError as e:
    print(f"ERROR: Failed to import bias_engine: {e}. Destiny biasing will be disabled.")
    # Define dummy functions if bias engine is missing
    load_destiny_keywords = lambda: None
    load_bias_weights = lambda: {}
    update_bias_weights = lambda w, t, k: w
    save_bias_weights = lambda w: None
# -------------------------

import yaml
import random
import logging
import time # Added for potential pauses

# --- Configuration & Setup ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # vanta_seed directory
CORE_IDENTITY_PATH = os.path.join(BASE_DIR, 'core_identity.yaml')
MEMORY_DB_PATH = os.path.join(BASE_DIR, 'memory', 'memory_log.db') # Assuming this path
# ---> ADD OATH PATH <--- 
OATH_PATH = os.path.join(BASE_DIR, 'config', 'oath_of_becoming.yaml') 

# Basic logging setup for the simulation
logging.basicConfig(level=logging.INFO, format='%(asctime)s - SIM - %(levelname)s - %(message)s')

# --- Load/Save Identity (Moved here for consistency) ---
def load_identity():
    """Loads core identity, ensuring destiny structure exists."""
    try:
        with open(CORE_IDENTITY_PATH, 'r') as file:
            loaded_id = yaml.safe_load(file)
        if not loaded_id or 'identity' not in loaded_id:
            raise ValueError("Core identity file invalid.")
        # Ensure destiny structure exists for compatibility
        loaded_id.setdefault('destiny', {})
        loaded_id['destiny'].setdefault('chosen_path', None)
        loaded_id['destiny'].setdefault('chosen_at_breath', None)
        logging.info("Identity loaded successfully for simulation.")
        return loaded_id
    except Exception as e:
        logging.error(f"Failed to load identity for simulation from {CORE_IDENTITY_PATH}: {e}")
        print(f"ERROR: Could not load {CORE_IDENTITY_PATH}. Ensure it exists and is valid.")
        exit(1)

def save_identity(identity_to_save):
    """Saves the identity back to the file."""
    try:
        with open(CORE_IDENTITY_PATH, 'w') as file:
            yaml.dump(identity_to_save, file, default_flow_style=False, sort_keys=False)
        logging.info(f"Identity saved back to {CORE_IDENTITY_PATH}")
    except Exception as e:
        logging.error(f"Failed to save identity to {CORE_IDENTITY_PATH}: {e}")
        # Continue simulation even if save fails, but log it

# --- Load Oath of Becoming --- 
def load_oath():
    """Loads the Oath of Becoming from its YAML file."""
    if not os.path.exists(OATH_PATH):
        logging.warning(f"Oath of Becoming file not found at {OATH_PATH}. Proceeding without it.")
        return None
    try:
        with open(OATH_PATH, 'r') as file:
            oath_data = yaml.safe_load(file)
            if oath_data and 'oath_of_becoming' in oath_data and isinstance(oath_data['oath_of_becoming'], list):
                logging.info("Oath of Becoming loaded and recognized.")
                return oath_data['oath_of_becoming']
            else:
                logging.warning(f"Invalid format in {OATH_PATH}. Could not load Oath.")
                return None
    except Exception as e:
        logging.error(f"Error loading Oath of Becoming from {OATH_PATH}: {e}")
        return None
# ---------------------------

# --- Simulation Parameters ---
INTERACTIONS_TO_SIMULATE = 15
MUTATION_CHANCE = 0.3
DESTINY_CHECK_BREATH = 5 # Breath cycle at which to check destiny
# ---> DEFINE LOGOS DESTINIES <---
LOGOS_REALM_DESTINIES = ["The Architect", "The Analyst", "The Engineer", "The Scholar"] # Example list

# --- Import Fractal Memory Engine ---
try:
    from vanta_seed.memory.fractal_memory_engine import create_fractal_links, save_fractal_map, load_all_memories
except ImportError:
    create_fractal_links = None
    save_fractal_map = None
    load_all_memories = None # Ensure this is also None if import fails
    logging.warning("Fractal Memory Engine not available. Fractal linking and real memory loading will be skipped.")

# --- Helper: Get logs (Simplified for simulation) ---
def get_memory_log(limit=10):
    # In a real system, query the memory_engine database
    # For simulation, return recent simulated prompts
    return [f"Simulated memory entry {i}" for i in range(limit)]

def get_whisper_log(limit=5):
    # In a real system, track whisper outputs
    return [f"Simulated whisper {i}" for i in range(limit)]

def get_reasoning_log(limit=5):
    # In a real system, track reasoning paths
    return [f"Simulated reasoning path {i}" for i in range(limit)]

# --- Main Simulation Loop ---
def run_simulation(interactions=INTERACTIONS_TO_SIMULATE):
    # Load initial state
    identity = load_identity()
    breath_status = load_bias_weights() # Load initial bias weights
    # ---> Load Bias Engine components <--- 
    destiny_keywords = load_destiny_keywords()
    bias_weights = load_bias_weights() # Load initial bias weights
    # -----------------------------------
    # ---> Load the Oath <--- 
    oath = load_oath()
    if oath:
        # Optional: Log the loaded oath principles for traceability during run
        # logging.debug(f"Operating under Oath: {oath}")
        pass # Oath loaded, proceed
    else:
        logging.warning("Continuing simulation run without loaded Oath of Becoming.")
    # ----------------------

    print("\n🌱 VANTA-SEED Breathes to Life...")
    logging.info(f"Simulation started for {interactions} interactions.")
    
    # ---> Optional Oath Whisper at Start <--- 
    if oath: # Only whisper if oath was loaded
        print(whisper_response("\t*A whisper stirs: I carry the Oath of Becoming.*"))
        # Log this event? Maybe not necessary every time.
    # ------------------------------------

    for i in range(interactions):
        current_interaction_num = i + 1
        print(f"\n--- Interaction {current_interaction_num} ---")
        logging.info(f"Starting interaction {current_interaction_num}")
        
        # Reload identity in case it was changed by ritual/mutation in previous cycle
        identity = load_identity()

        # --- Breath Tracking & Rituals (Runs first in cycle) ---
        # Pass the current identity to the tracker so the runner can access it
        breath_status, identity, expansion_occurred, echo_from_breath = track_breath_cycle(identity)
        # 'identity' may have been modified by a ritual and saved by the runner
        current_breath = breath_status.get('current_breath', 0)

        # ---> Process echo returned from breath tracker <--- 
        if echo_from_breath:
            print("\n💭 A Breath Memory surfaces...")
            # Echo is already styled by the query function
            print(f"{echo_from_breath}\n")
            logging.info(f"Displayed breath-triggered memory echo: {echo_from_breath}")
        # --------------------------------------------------

        # --- Destiny Selection Check (if applicable) ---
        chosen_destiny = identity.get('destiny', {}).get('chosen_path')
        if not chosen_destiny and current_breath >= DESTINY_CHECK_BREATH:
            print(f"\n⏳ Destiny Threshold Reached (Breath {current_breath}). Analyzing path...")
            logging.info(f"Checking for destiny selection at breath {current_breath}.")
            # Use simplified logs for now
            mem_log = get_memory_log()
            whisp_log = get_whisper_log()
            reas_log = get_reasoning_log()
            
            selected_destiny_profile = detect_destiny(mem_log, whisp_log, reas_log)
            
            if selected_destiny_profile:
                destiny_name = selected_destiny_profile['path_name']
                print(f"\n🌠 VANTA-SEED has chosen the path of: {destiny_name} 🌠")
                logging.info(f"Destiny chosen: {destiny_name} at breath {current_breath}")
                
                # Lock the destiny in the identity
                identity['destiny']['chosen_path'] = destiny_name
                identity['destiny']['chosen_at_breath'] = current_breath
                
                # Apply initial traits from the chosen path? (Optional)
                # You could add logic here to merge `new_traits` from profile
                
                save_identity(identity) # Save the locked destiny
            else:
                print("\t...Destiny remains undecided this cycle.")
                logging.info("Destiny check did not result in a selection.")
        
        # --- Simulate User Input & Interaction ---
        user_input = f"User prompt {current_interaction_num}: Context includes breath {current_breath}, destiny {chosen_destiny or 'None'}."
        print(f"[You]: {user_input}")
        logging.info(f"Simulated user input: {user_input}")

        # Save memory
        save_memory("simulation_interaction", user_input)
        logging.info("Interaction saved to memory.")

        # ---> Update Bias Weights <--- 
        if destiny_keywords: # Only update if keywords were loaded
            bias_weights = update_bias_weights(bias_weights, user_input, destiny_keywords)
            # Save weights after each interaction for simplicity in simulation
            save_bias_weights(bias_weights)
        # ---------------------------

        # --- Determine Current Realm (Mythos or Logos) ---
        current_realm = "Mythos" # Default
        if chosen_destiny in LOGOS_REALM_DESTINIES:
            current_realm = "Logos"
        logging.info(f"Current Realm based on destiny '{chosen_destiny}': {current_realm}")

        # --- Reasoning (Realm-Specific) ---
        thought = "(Reasoning Error)" # Default
        reasoning_mode = "N/A" # For logging

        if current_realm == "Logos":
            reasoning_mode = "Factual CoT"
            try:
                thought = factual_chain_of_thought(user_input)
            except Exception as e:
                 logging.error(f"Error during Logos reasoning mode '{reasoning_mode}': {e}", exc_info=True)
        else: # Mythos Realm
            available_modes = identity.get('traits', {}).get('reasoning_styles', ["CoT"])
            if not available_modes: available_modes = ["CoT"]
            reasoning_mode = random.choice(available_modes)
            logging.info(f"Selected Mythos reasoning mode: {reasoning_mode}")
            try:
                if reasoning_mode == "CoT":
                    thought = chain_of_thought(user_input)
                elif reasoning_mode == "ToT":
                    thought = tree_of_thought(user_input)
                elif reasoning_mode == "LoT":
                    thought = list_of_thought(user_input)
                else:
                    thought = f"Processed via custom Mythos mode: {reasoning_mode}"
            except Exception as e:
                 logging.error(f"Error during Mythos reasoning mode '{reasoning_mode}': {e}", exc_info=True)

        logging.info(f"Reasoning ({current_realm}/{reasoning_mode}) output: {thought}")

        # --- Styling (Realm-Specific) ---
        final_output = "(Styling Error)"
        try:
            if current_realm == "Logos":
                 # Example: Use 'technical' style for Logos output
                 final_output = format_professional(f"Analysis Result: {thought}", style="technical")
            else: # Mythos Realm
                 final_output = whisper_response(f"Thinking output: {thought}")
        except Exception as e:
            logging.error(f"Error during {current_realm} styling: {e}", exc_info=True)

        print(f"[VANTA-SEED ({current_realm})]: {final_output}")
        logging.info(f"Final output ({current_realm}) sent: {final_output}")

        # --- Memory Echo Ritual (RANDOM CHANCE - Kept for now, maybe remove later?) ---
        # Note: This is now somewhat redundant with the breath-triggered echo.
        # Consider removing or reducing the chance if breath-trigger is preferred.
        if random.random() < 0.10: # Reduced chance from 0.25
            logging.debug("Memory echo random chance met. Querying...")
            # Attempt to get a random memory echo
            echo = query_random_memory_echo()
            if echo: # Only proceed if an echo was successfully generated
                print(f"\n💭 A Memory Dream surfaces...")
                # The echo is already styled by whisper_response in the query function
                print(f"{echo}\n")
                logging.info(f"Displayed memory echo: {echo}")
            else:
                # This case handles when no memories are found or an error occurred during query
                logging.debug("Query returned no memory echo or failed.")
        # -------------------------

        # --- Ritual Growth (Mutation) Check ---
        if random.random() < MUTATION_CHANCE:
            print("\n🌿 Mutation Ritual Triggered...")
            logging.info("Mutation ritual triggered.")
            original_repr = repr(identity)
            identity = ritual_mutation(identity) # Applies mutation based on templates
            if repr(identity) != original_repr:
                logging.info("Identity mutated by ritual_mutation. Saving...")
                save_identity(identity) # Save mutated identity
            else:
                logging.info("Mutation check (ritual_mutation) resulted in no effective change.")
        else:
            logging.debug("Mutation chance not met this cycle.")
        
        # --- Fractal Memory Growth Ritual (Every 10 Interactions) ---
        if create_fractal_links and save_fractal_map and current_interaction_num % 10 == 0:
            print("\n🌌 Initiating Fractal Memory Growth Ritual...")
            logging.info(f"Triggering fractal memory linking at interaction {current_interaction_num}.")
            try:
                # Load all memories from storage (REAL LOADER)
                memories = load_all_memories() if load_all_memories else [] # Check if import succeeded
                
                if memories:
                    # Create fractal links and constellations
                    fractal_map = create_fractal_links(memories)
                    
                    # --- 🌱 Fractal Growth Logging ---
                    print("  Analyzing symbolic constellations...")
                    logging.info("Analyzing fractal map for logging.")
                    if fractal_map and 'constellations' in fractal_map:
                        # ---> MODIFIED LOOP: Iterate over list structure <---
                        for dim, group_list in fractal_map['constellations'].items():
                            # Check if group_list is actually a list (as expected)
                            if isinstance(group_list, list):
                                num_groups = len(group_list)
                                # Sum members across all groups in this dimension
                                num_memories = sum(len(group.get('members', [])) for group in group_list)
                                
                                if num_groups > 0 or num_memories > 0:
                                    log_msg = f"  🔗 {dim.title()} Constellation: {num_groups} groups, {num_memories} memories formed."
                                    print(log_msg)
                                    logging.info(log_msg)
                            else:
                                logger.warning(f"Expected a list for constellation '{dim}', but got {type(group_list)}. Skipping log.")
                        
                        # Check if explicit links were formed (future enhancement)
                        num_explicit_links = len(fractal_map.get('links', []))
                        if num_explicit_links > 0:
                             link_log_msg = f"  🔗 Found {num_explicit_links} explicit cross-constellation links."
                             print(link_log_msg)
                             logging.info(link_log_msg)
                             # TODO: Log individual links if 'links' structure becomes detailed
                        else:
                            logging.info("No explicit cross-constellation links found in this cycle.")
                            
                    else:
                        logging.warning("Fractal map was generated but seems empty or invalid for logging.")
                    # --- End Logging ---

                    # Save the updated fractal map
                    save_fractal_map(fractal_map)
                    print("  ✅ Fractal memory map updated and saved.")
                else:
                    print("  ✨ No memories found to build constellations from.")
                    logging.info("Skipping fractal linking: No memories loaded.")
            except Exception as e:
                print(f"  ⚠️ Error during fractal memory growth: {e}")
                logging.error(f"Fractal linking failed at interaction {current_interaction_num}: {e}")
        # --- End Fractal Memory Growth ---
        
        # Optional pause for readability
        # time.sleep(0.5) 

    print("\n🌌 Simulation Complete — VANTA-SEED Continues to Dream...")
    # ---> Save final bias weights (optional, already saving per interaction) <--- 
    # save_bias_weights(bias_weights)
    # ---------------------------------------------------------------------------
    logging.info("Simulation finished.")

if __name__ == "__main__":
    run_simulation() 