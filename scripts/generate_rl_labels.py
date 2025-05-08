"""
VANTA Kernel - RL Training Label Generation

Generates training data (state, action, reward, next_state tuples) for the
Reinforcement Learning (RL) system by correlating efficacy scores with the
events/contexts that led to the corresponding actions (protocol triggers).
"""

import logging
import sys
import os
import csv
import json
import utils # Use the centralized loaders
from collections import defaultdict
from datetime import datetime

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - RL_LABEL_GEN - %(levelname)s - %(message)s')

# Define output path
OUTPUT_CSV_PATH = "data/rl_training_labels.csv"


def derive_state_representation(event_data: dict | None) -> str:
    """Derives a JSON string state representation from event/context data."""
    if not event_data or not isinstance(event_data, dict):
        return json.dumps({"state": "unknown_or_invalid_data"})
        
    # Example: Select and sort key features. Adapt based on actual event log structure.
    state_features = {
        "event_type": event_data.get("type", "unknown"),
        "payload_summary": str(event_data.get("payload", {}))[:100],
        "context_variable": event_data.get("context_variable"),
        "app_context": event_data.get("app_context")
    }
    # Filter out None values for cleaner representation
    state_features = {k: v for k, v in state_features.items() if v is not None}
    return json.dumps(state_features, sort_keys=True)

def derive_reward(efficacy_record: dict) -> float:
    """Maps efficacy score (0-1) to a reward signal (-1 to 1)."""
    score = efficacy_record.get("final_score", 0.5) # Default to neutral if score missing
    if not isinstance(score, (int, float)):
        logging.warning(f"Invalid efficacy score type ({type(score)}): {score} in record {efficacy_record.get('strategy_id')}. Defaulting reward to 0.")
        return 0
    
    if score >= 0.75:
        return 1
    elif score >= 0.4:
        return 0
    else:
        return -1

def generate_labels(triggers: list, efficacy_data: list, event_logs: list) -> list:
    """Generates RL training labels by correlating efficacy and event logs."""
    labeled_examples = []
    
    if not efficacy_data:
        logging.warning("No efficacy data loaded. Cannot generate labels.")
        return []
    if not event_logs:
         logging.warning("No event context logs loaded. Cannot determine state for labels.")
         # Decide behavior: return empty, or generate labels with placeholder state?
         # For now, return empty as state is critical.
         return []

    # --- Pre-processing: Create lookups for efficient correlation --- 
    
    # Create a lookup for event logs by their assumed unique ID
    # Assumes event logs have an "event_id" key and a "timestamp" key
    event_lookup = {} 
    sorted_event_logs = sorted(event_logs, key=lambda x: x.get("timestamp", 0)) # Sort by timestamp
    
    for i, log in enumerate(sorted_event_logs):
        event_id = log.get("event_id")
        if event_id:
            event_lookup[event_id] = {
                "data": log, 
                "index": i # Store index for finding next state
            }
        else:
            logging.warning(f"Event log entry missing 'event_id': {log}")

    logging.info(f"Created lookup for {len(event_lookup)} event logs with IDs.")

    # --- Generate Labels --- 
    skipped_records = 0
    for record in efficacy_data:
        action_id = record.get("strategy_id") # Action = the trigger/strategy used
        event_ref = record.get("event_context_ref") # Link to the originating event
        efficacy_score = record.get("final_score")
        
        if not action_id or not event_ref or efficacy_score is None:
            logging.warning(f"Skipping efficacy record due to missing fields: {record}")
            skipped_records += 1
            continue

        # Find the state (event data) that led to this action
        state_event_info = event_lookup.get(event_ref)
        if not state_event_info:
            logging.warning(f"Could not find event log context for event_ref '{event_ref}' in efficacy record for action '{action_id}'. Skipping label.")
            skipped_records += 1
            continue
            
        state_data = state_event_info["data"]
        state_representation = derive_state_representation(state_data)
        reward = derive_reward(record)

        # Find the next state (using the next event log entry after the current one)
        current_event_index = state_event_info["index"]
        next_state_representation = json.dumps({"terminal": True}) # Default if no next state
        if current_event_index + 1 < len(sorted_event_logs):
            next_state_data = sorted_event_logs[current_event_index + 1]
            next_state_representation = derive_state_representation(next_state_data)
            
        # Append example (State, Action, Reward, Next State)
        labeled_examples.append({
            "state": state_representation,
            "action": action_id, 
            "reward": reward,
            "next_state": next_state_representation,
            "timestamp": record.get("timestamp"), # Timestamp of efficacy record
            "event_id_ref": event_ref
        })

    if skipped_records > 0:
        logging.warning(f"Skipped {skipped_records} efficacy records due to missing links or data.")
    logging.info(f"Generated {len(labeled_examples)} RL training examples." )
    return labeled_examples

def save_labels_to_csv(labels: list, output_path: str):
    """Saves the generated labels to a CSV file."""
    if not labels:
        logging.warning("No labels generated, skipping CSV write.")
        return False
        
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            logging.info(f"Created directory: {output_dir}")
        except OSError as e:
            logging.error(f"Failed to create directory {output_dir}: {e}")
            return False
            
    try:
        fieldnames = labels[0].keys() # Assumes all dicts have same keys
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(labels)
        logging.info(f"Successfully wrote {len(labels)} labels to {output_path}")
        return True
    except IOError as e:
        logging.error(f"Failed to write labels to {output_path}: {e}")
        return False
    except Exception as e:
        logging.exception(f"An unexpected error occurred saving labels: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    print("[RL Label Generation] Starting...")
    
    # Load necessary data using utils
    # Note: Ensure trigger_registry is actually needed by label generation logic
    # It might only be needed if actions need validation against known triggers.
    # trigger_registry = utils.load_trigger_registry()
    efficacy_records = utils.load_efficacy_data() 
    event_log_data = utils.load_event_context_logs() # Still placeholder loader
    
    # Basic check for loaded data
    if efficacy_records is None or event_log_data is None:
        print("[RL Label Generation] Failed: Could not load required efficacy or event log data (or files missing/invalid). Check logs.")
        sys.exit(1)
        
    # Generate labels
    generated_labels = generate_labels([], efficacy_records, event_log_data) # Pass empty trigger list for now
    
    # Save labels
    if save_labels_to_csv(generated_labels, OUTPUT_CSV_PATH):
        print(f"[RL Label Generation] Finished successfully. Labels saved to {OUTPUT_CSV_PATH}.")
        sys.exit(0)
    else:
        print("[RL Label Generation] Finished, but failed to save labels (or no labels generated). Check logs.")
        # Exit with 0 if labels were generated but saving failed, 1 if generation itself failed early
        sys.exit(1 if not generated_labels else 0) 