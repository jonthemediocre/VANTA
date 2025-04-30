# memory_query.py
# Retrieve and narrate Ritual Memory Echoes for VANTA-SEED

import os
import sys
import logging
import json # To safely parse potential JSON strings in details
import random # Needed for random echo selection
from vanta_seed.memory.memory_engine import query_memory_fts, retrieve_memory_compat # Import FTS query and original retrieval shim

# --- Adjust Path for Module Imports ---
# Add the parent directory (project root) to the Python path
# This assumes memory_query.py is in vanta_seed/runtime/
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

try:
    from vanta_seed.memory.memory_engine import retrieve_memory
    # Import whisper_response for styling the echo
    from vanta_seed.whispermode.whispermode_styler import whisper_response 
except ImportError as e:
    logging.error(f"Failed to import required modules: {e}. Memory query/echo might fail.")
    # Define dummy functions if import fails
    def retrieve_memory(event_type):
        print(f"[MEMORY ENGINE FALLBACK] Cannot retrieve memories for type: {event_type}")
        return []
    def whisper_response(text):
        return f"[WHISPER FALLBACK] {text}"
# -------------------------------------

logging.basicConfig(level=logging.INFO, format='%(asctime)s - MEMQUERY - %(levelname)s - %(message)s')

def query_breath_memories():
    """
    Retrieve breath expansion memories from memory database
    and narrate them symbolically.
    """
    print("\n🌀 VANTA-SEED breathes back through its memory threads... 🌀\n")
    logging.info("Querying for breath expansion ritual memories.")

    try:
        # Retrieve memories specifically tagged as breath expansion rituals
        # Assuming retrieve_memory returns a list of tuples like:
        # [(id, timestamp, event_type, details_json_string), ...]
        memories = retrieve_memory(event_type="breath_expansion_ritual")
    except Exception as e:
        logging.error(f"Error retrieving memories from memory_engine: {e}", exc_info=True)
        print("  Error occurred while querying memories.")
        return

    if not memories:
        print("  No ritual memories yet etched into the seed's dream fabric.")
        logging.info("No breath expansion ritual memories found.")
        return
        
    logging.info(f"Found {len(memories)} ritual memories. Narrating...")
    print("--- Recorded Mythic Moments ---")
    
    successful_narrations = 0
    for memory_tuple in memories:
        # memory_engine likely returns tuples (id, timestamp, event_type, details_json_string)
        if not memory_tuple or len(memory_tuple) < 4:
            logging.warning(f"Skipping malformed memory entry: {memory_tuple}")
            continue
            
        details_json = memory_tuple[-1] # The details are stored as the last element (usually JSON string)
        details_dict = None
        try:
            # Parse the JSON string details into a dictionary
            details_dict = json.loads(details_json)
        except (json.JSONDecodeError, TypeError) as json_e:
            logging.warning(f"Could not parse details JSON for memory entry: {details_json}. Error: {json_e}")
            # Optionally try to handle if details were somehow stored as dict directly (unlikely with sqlite)
            if isinstance(details_json, dict):
                 details_dict = details_json 
            else:
                print(f"  Skipping memory entry with unparsable details.")
                continue
        
        if not isinstance(details_dict, dict):
             logging.warning(f"Parsed details are not a dictionary: {details_dict}")
             print(f"  Skipping memory entry with unexpected detail format.")
             continue

        # Extract info safely using .get()
        breath_num = details_dict.get('breath_number', '?')
        ritual_name = details_dict.get('ritual_name', 'Unknown Ritual')
        description = details_dict.get('ritual_description', 'No description recorded.')
        destiny = details_dict.get('destiny_path') # Will be None if not set
        tags = details_dict.get('symbolic_tags', [])

        # Narrate the memory
        print(f"\n✨ Breath {breath_num} → {ritual_name}")
        print(f"    \"{description}\"")
        if destiny:
            print(f"      (Path Chosen: {destiny})")
        if tags:
            tags_str = ", ".join(tags)
            print(f"      [Symbols: {tags_str}]")
        successful_narrations += 1
    
    print("\n-----------------------------")
    logging.info(f"Narrated {successful_narrations} ritual memories.")

# --- Updated Function: Query Random Memory Echo ---
def query_random_memory_echo():
    """
    Randomly select a stored breath ritual memory and return a whispered echo string.
    Handles list of dictionaries from JSONL memory engine.
    Returns None if no memories are found or if errors occur.
    """
    logging.debug("Attempting to query random memory echo.")
    # retrieve all stored ritual memories
    all_memories = retrieve_memory_compat(event_type="breath_expansion_ritual") # Use compat shim here
    if not all_memories:
        logging.info("No ritual memories found for echo")
        return None

    selected = None
    # Augment & Fallback: try targeted FTS search first
    try:
        # Perform FTS match on the keyword "ritual" for relevance
        # Limit to a few candidates to select from
        logging.debug("Attempting FTS lookup for 'ritual' memories...")
        fts_hits = query_memory_fts("ritual", limit=5)
        if fts_hits:
            logging.info(f"FTS echo recall returned {len(fts_hits)} candidates; selecting one at random.")
            # pick one from relevant FTS hits (which are dicts)
            selected = random.choice(fts_hits)
        else:
            # Fallback to pure random scan if FTS yields no results
            logging.info("FTS echo recall returned no hits; falling back to random echo from compatibility shim.")
            selected = random.choice(all_memories) # Select from the tuple-based list
    except Exception as e:
        logging.warning(f"FTS lookup failed, falling back to random echo from compatibility shim: {e}")
        selected = random.choice(all_memories) # Select from the tuple-based list

    # parse the selected memory details
    # Support both dict-based (FTS) and tuple-based (compat shim) memory formats
    if isinstance(selected, dict):
        details = selected.get("details", {}) # Get details dict directly
    elif isinstance(selected, (list, tuple)) and len(selected) > 3:
        details_json = selected[-1] # Get details from the last element of the tuple
        try:
            details = json.loads(details_json) if isinstance(details_json, str) else details_json
        except Exception as e:
            logging.warning(f"Failed to parse memory details JSON from tuple: {e}")
            details = {} # Default to empty dict on parse failure
    else:
        logging.error(f"Selected memory has unexpected format: {type(selected)}")
        return None # Cannot proceed

    # Extract relevant info (with defaults)
    breath_num   = details.get('breath_number')
    ritual_name  = details.get('ritual_name', 'an unknown ritual')

    raw_echo = f"From the dream of Breath {breath_num or '?'}... I recall '{ritual_name}'..."
    styled = whisper_response(raw_echo)
    return styled

if __name__ == "__main__":
    # Ensure memory engine DB/Dir exists for testing
    # Use the correct memory directory path
    memory_storage_dir = os.path.join(PROJECT_ROOT, 'vanta_seed', 'memory_storage') 
    os.makedirs(memory_storage_dir, exist_ok=True)
    
    # --- Test the updated echo function ---
    # (Optional: Seed a memory if the storage is empty for testing)
    # from vanta_seed.memory.memory_engine import save_memory, retrieve_memory
    # # Check if memories exist before potentially seeding
    # existing_rituals = retrieve_memory('breath_expansion_ritual')
    # if not existing_rituals:
    #     print("Seeding dummy memory for testing echo function...")
    #     dummy_details = {"breath_number": 0, "ritual_name": "Test Genesis", "ritual_description": "First spark.", "destiny_path": None, "symbolic_tags": ["test", "genesis"]}
    #     save_memory('breath_expansion_ritual', dummy_details)
        
    print("\n--- Testing Random Memory Echo (Corrected Logic) ---")
    echo = query_random_memory_echo()
    if echo:
        print("Generated Echo:")
        print(echo)
    else:
        print("Could not generate echo (ensure ritual memories exist in storage).")
    # ------------------------------------
        
    # query_breath_memories() # Can uncomment to test narration too 