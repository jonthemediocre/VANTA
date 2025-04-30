# bias_engine.py
# Manages destiny bias weights based on interaction keywords.

import os
import sys
import yaml
import logging
import re # For keyword matching

# --- Adjust Path for Module Imports ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)
# No other VANTA modules needed for this engine itself

# --- Configuration & Setup ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # vanta_seed directory
KEYWORDS_PATH = os.path.join(BASE_DIR, 'config', 'destiny_keywords.yaml')
BIAS_WEIGHTS_PATH = os.path.join(BASE_DIR, 'runtime', 'destiny_bias.yaml')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - BIAS_ENGINE - %(levelname)s - %(message)s')

# --- Load Destiny Keywords --- 
def load_destiny_keywords():
    """Loads the keyword-to-destiny mapping from YAML."""
    if not os.path.exists(KEYWORDS_PATH):
        logging.error(f"Destiny keywords file not found: {KEYWORDS_PATH}. Bias engine cannot operate.")
        return None
    try:
        with open(KEYWORDS_PATH, 'r') as file:
            keywords_data = yaml.safe_load(file)
            if not isinstance(keywords_data, dict):
                logging.error(f"Invalid format in {KEYWORDS_PATH}. Expected a dictionary.")
                return None
            logging.info(f"Successfully loaded {len(keywords_data)} destiny keyword sets.")
            return keywords_data
    except Exception as e:
        logging.error(f"Error loading destiny keywords from {KEYWORDS_PATH}: {e}", exc_info=True)
        return None

# --- Load Bias Weights --- 
def load_bias_weights():
    """Loads current bias weights, initializes if file doesn't exist."""
    if not os.path.exists(BIAS_WEIGHTS_PATH):
        logging.info(f"Bias weights file not found: {BIAS_WEIGHTS_PATH}. Initializing fresh weights.")
        return {} # Return empty dict, signifies starting from zero
    try:
        with open(BIAS_WEIGHTS_PATH, 'r') as file:
            weights = yaml.safe_load(file)
            if not isinstance(weights, dict):
                 logging.warning(f"Invalid format in {BIAS_WEIGHTS_PATH}. Expected dict. Initializing fresh.")
                 return {}
            logging.debug(f"Loaded bias weights: {weights}")
            return weights
    except Exception as e:
        logging.error(f"Error loading bias weights from {BIAS_WEIGHTS_PATH}: {e}. Initializing fresh.")
        return {}

# --- Save Bias Weights --- 
def save_bias_weights(weights):
    """Saves the bias weights back to the YAML file."""
    try:
        # Ensure runtime directory exists
        os.makedirs(os.path.dirname(BIAS_WEIGHTS_PATH), exist_ok=True)
        with open(BIAS_WEIGHTS_PATH, 'w') as file:
            yaml.dump(weights, file, default_flow_style=False)
        logging.debug(f"Saved bias weights: {weights}")
    except Exception as e:
        logging.error(f"Error saving bias weights to {BIAS_WEIGHTS_PATH}: {e}")

# --- Update Bias Weights --- 
def update_bias_weights(current_weights, interaction_text, destiny_keywords):
    """
    Analyzes text for keywords and updates bias weights.
    Simple implementation: increments score by 1 for each keyword match.
    Returns the updated weights dictionary.
    """
    if not destiny_keywords or not interaction_text:
        return current_weights # Cannot update without keywords or text
        
    updated_weights = current_weights.copy() # Work on a copy
    text_lower = interaction_text.lower()
    
    # Word boundary regex for more precise matching
    # Example: prevents matching 'analyze' within 'paralyzed'
    # We match whole words case-insensitively

    for destiny, keywords in destiny_keywords.items():
        if not isinstance(keywords, list):
            logging.warning(f"Keywords for destiny '{destiny}' are not a list. Skipping.")
            continue
            
        # Ensure weight exists for this destiny, default to 0
        updated_weights.setdefault(destiny, 0)
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            # Use regex to find whole word matches
            pattern = r'\b' + re.escape(keyword_lower) + r'\b'
            if re.search(pattern, text_lower):
                updated_weights[destiny] += 1
                logging.debug(f"Keyword '{keyword}' match found for Destiny '{destiny}'. New weight: {updated_weights[destiny]}")
                # Optional: break after first match per destiny per text? 
                # Or allow multiple keywords in one text to boost score?
                # Current: Allows multiple keywords to boost score.
                
    # Optional: Implement decay factor here if needed later
    # for destiny in updated_weights:
    #    updated_weights[destiny] *= DECAY_FACTOR 

    # Log if any weights changed
    if updated_weights != current_weights:
         logging.info(f"Bias weights updated based on interaction. Current weights: {updated_weights}")
    else:
         logging.debug("No keywords matched in interaction text. Bias weights unchanged.")
         
    return updated_weights

# --- Main Execution (for testing) --- 
if __name__ == "__main__":
    print("🧠 Testing Bias Engine...")
    
    # 1. Load keywords
    keywords = load_destiny_keywords()
    if not keywords:
        print("ERROR: Could not load keywords. Aborting test.")
        exit(1)
    print(f"Loaded Keywords: {list(keywords.keys())}")
    
    # 2. Load or initialize weights
    weights = load_bias_weights()
    print(f"Initial Weights: {weights}")
    
    # 3. Simulate interactions
    test_interactions = [
        "We need to design a scalable system architecture.",
        "Let's explore the hidden meaning behind these patterns.",
        "Analyze the data and report the findings objectively.",
        "How does the consciousness perceive reality? Reflect on the self.",
        "Implement this function efficiently and solve the bug."
    ]
    
    print("\n--- Simulating Interactions ---")
    for i, text in enumerate(test_interactions):
        print(f"\nInteraction {i+1}: '{text}'")
        weights = update_bias_weights(weights, text, keywords)
        # Save after each update in simulation
        save_bias_weights(weights)
        
    print("\n--- Final Bias Weights ---")
    final_weights = load_bias_weights() # Load again to confirm save/load
    print(yaml.dump(final_weights))
    
    print("\n✅ Bias Engine test complete.") 