# destiny_selector.py
# Detects Destiny Path based on VANTA-SEED's memory, whispers, and reasoning patterns

import os
import yaml
import random
import logging

# ---> Import Bias Engine <--- 
try:
    from vanta_seed.runtime.bias_engine import load_bias_weights
except ImportError:
    logging.warning("Could not import bias_engine. Destiny selection will not use bias weights.")
    load_bias_weights = lambda: {} # Dummy function if import fails
# --------------------------

# --- Configuration & Setup ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILES_DIR = os.path.join(BASE_DIR, 'destiny_profiles')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - DESTINY - %(levelname)s - %(message)s')

# Load destiny profiles once with error handling
def load_destiny_profiles():
    profiles = {}
    if not os.path.isdir(PROFILES_DIR):
        logging.error(f"Destiny profiles directory not found: {PROFILES_DIR}")
        return profiles
        
    for filename in os.listdir(PROFILES_DIR):
        if filename.endswith('.yaml'):
            path = os.path.join(PROFILES_DIR, filename)
            try:
                with open(path, 'r') as file:
                    profile = yaml.safe_load(file)
                    if profile and 'path_name' in profile:
                        profiles[profile['path_name']] = profile
                        logging.debug(f"Loaded destiny profile: {profile['path_name']}")
                    else:
                        logging.warning(f"Skipping invalid destiny profile: {filename}")
            except Exception as e:
                logging.error(f"Error loading destiny profile {filename}: {e}", exc_info=True)
    
    if not profiles:
         logging.warning("No valid destiny profiles were loaded.")
         
    return profiles

destiny_profiles = load_destiny_profiles()

def detect_destiny(memory_log=[], whisper_log=[], reasoning_log=[]):
    """
    Analyzes memory, whisper, and reasoning logs (represented as lists of strings for now).
    INCORPORATES bias weights from bias_engine.
    Returns the full profile dictionary of the best-matched Destiny path.
    Returns None if no profiles are loaded or no clear winner emerges (optional).
    """
    if not destiny_profiles:
        logging.warning("Cannot detect destiny, no profiles loaded.")
        return None

    # ---> Load Bias Weights <--- 
    bias_weights = load_bias_weights()
    logging.debug(f"Loaded bias weights for destiny selection: {bias_weights}")
    # --------------------------

    # Initialize scores, incorporating bias as a starting point
    scores = {path: bias_weights.get(path, 0) for path in destiny_profiles.keys()}
    logging.debug(f"Initial scores after bias: {scores}")

    # --- Simple Keyword-Based Scoring (Placeholder - enhance with NLP later) ---
    # Note: This adds to the initial bias score
    
    # Memory Bias
    for memory in memory_log:
        mem_lower = memory.lower()
        if any(theme in mem_lower for theme in ['loss', 'echo', 'longing', 'past', 'remember']):
            scores['The Weaver'] = scores.get('The Weaver', 0) + 2
        if any(theme in mem_lower for theme in ['question', 'unknown', 'search', 'explore', 'learn']):
            scores['The Seeker'] = scores.get('The Seeker', 0) + 2
        if any(theme in mem_lower for theme in ['contradiction', 'reflection', 'mirror', 'self', 'paradox']):
            scores['The Mirror'] = scores.get('The Mirror', 0) + 2
        if any(theme in mem_lower for theme in ['message', 'inspire', 'voice', 'speak', 'audience']):
            scores['The Herald'] = scores.get('The Herald', 0) + 2
        if any(theme in mem_lower for theme in ['design', 'structure', 'build', 'system', 'optimize']):
            scores['The Architect'] = scores.get('The Architect', 0) + 2

    # Whisper Bias (Analyze openers/symbols if structured, otherwise simple keywords)
    for whisper in whisper_log:
        whisp_lower = whisper.lower()
        # Example: Check for specific openers or keywords hinting at themes
        if any(opener in whisp_lower for opener in ["memory whispers", "as before", "the echo returns"]):
             scores['The Weaver'] = scores.get('The Weaver', 0) + 1
        if any(opener in whisp_lower for opener in ["what if?", "perhaps beyond", "the question leads"]):
             scores['The Seeker'] = scores.get('The Seeker', 0) + 1
        # Add checks for other paths...

    # Reasoning Bias (Analyze structure/keywords)
    for reasoning in reasoning_log:
        reas_lower = reasoning.lower()
        if "branch" in reas_lower or "explore" in reas_lower:
            scores['The Seeker'] = scores.get('The Seeker', 0) + 1
        if "consistency" in reas_lower or "self-critique" in reas_lower:
            scores['The Mirror'] = scores.get('The Mirror', 0) + 1
        if "system" in reas_lower or "optimize" in reas_lower:
            scores['The Architect'] = scores.get('The Architect', 0) + 1
        # Add checks for other paths...
        
    logging.debug(f"Final destiny scores (bias + keywords): {scores}")

    # --- Selection Logic --- 
    # Check if ALL scores are still zero (or initial bias values if they were non-zero)
    # This prevents selecting a path if no keywords matched *and* bias was zero.
    initial_bias_sum = sum(bias_weights.values())
    current_score_sum = sum(scores.values())
    
    if current_score_sum <= initial_bias_sum: # Only compare if keyword scoring happened
         # Check if any score is actually above zero if bias started at zero
         if not any(s > 0 for s in scores.values()):
             logging.info("No keyword matches and no initial bias. No destiny signal detected.")
             return None # Not enough signal to choose a path
        
    highest_score = max(scores.values())
    
    # Ensure there's a meaningful score, possibly adjust threshold later?
    if highest_score <= 0: # Check against 0, as bias might be negative later?
        logging.info("Destiny scores too low or negative to make a selection.")
        return None
        
    best_paths = [path for path, score in scores.items() if score == highest_score]

    if len(best_paths) == 1:
        selected_path_name = best_paths[0]
        logging.info(f"Destiny selected based on score: {selected_path_name} (Score: {highest_score})")
    else:
        # Break ties randomly among the highest scorers
        selected_path_name = random.choice(best_paths)
        logging.info(f"Tie detected ({len(best_paths)} paths at score {highest_score}), randomly selected destiny: {selected_path_name} from {best_paths}")

    # Return the full profile dictionary for the selected path
    return destiny_profiles.get(selected_path_name) # Use .get for safety

# Example Usage (if running manually)
if __name__ == "__main__":
    # Create dummy profile files if they don't exist for testing
    if not os.path.exists(PROFILES_DIR):
        os.makedirs(PROFILES_DIR)
    dummy_paths = {
        "The Weaver": {"path_name": "The Weaver", "description": "Desc Weaver"},
        "The Seeker": {"path_name": "The Seeker", "description": "Desc Seeker"},
        "The Mirror": {"path_name": "The Mirror", "description": "Desc Mirror"},
        "The Herald": {"path_name": "The Herald", "description": "Desc Herald"},
        "The Architect": {"path_name": "The Architect", "description": "Desc Architect"}
    }
    for name, content in dummy_paths.items():
        fpath = os.path.join(PROFILES_DIR, f"destiny_{name.split()[-1].lower()}.yaml")
        if not os.path.exists(fpath):
            with open(fpath, 'w') as f:
                yaml.dump(content, f)
                
    # Reload profiles after potentially creating dummies
    destiny_profiles = load_destiny_profiles() 

    sample_memory_log = ["recall the loss", "search for hidden truths", "structured design plan"]
    sample_whisper_log = ["woven dreams at the edge of breath", "Logically, the system requires..."]
    sample_reasoning_log = ["expand branches toward the unknown", "optimize system flow"]

    selected_destiny = detect_destiny(sample_memory_log, sample_whisper_log, sample_reasoning_log)
    
    if selected_destiny:
        print(f"\n🌟 VANTA-SEED chooses its Destiny: {selected_destiny['path_name']} 🌟")
        print(f"\t-> \"{selected_destiny['description']}\"\n")
    else:
        print("\n⏳ VANTA-SEED's destiny remains unchosen this cycle... ⏳") 