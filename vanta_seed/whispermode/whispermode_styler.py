# whispermode_styler.py
# Whispered Surreal Expression with Dynamic Phrasing
import json
import random
import os
import logging # Added for error handling

# Determine the correct path to the config directory relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, '..', 'config')
DICTIONARY_PATH = os.path.join(CONFIG_DIR, 'surreal_dictionary.json')

# Load surreal dictionary once with error handling
def load_surreal_dictionary():
    """Loads the surreal dictionary from the config folder."""
    try:
        with open(DICTIONARY_PATH, 'r') as file:
            data = json.load(file)
            # Basic validation
            if not isinstance(data.get('openers'), list) or \
               not isinstance(data.get('themes'), list) or \
               not isinstance(data.get('symbols'), list):
                logging.warning(f"Surreal dictionary at {DICTIONARY_PATH} is missing expected lists (openers, themes, symbols). Using defaults.")
                return None
            logging.info(f"Successfully loaded surreal dictionary from {DICTIONARY_PATH}")
            return data
    except FileNotFoundError:
        logging.error(f"ERROR: Surreal dictionary not found at {DICTIONARY_PATH}. Using defaults.")
        return None
    except json.JSONDecodeError:
        logging.error(f"ERROR: Could not decode JSON from {DICTIONARY_PATH}. Using defaults.")
        return None
    except Exception as e:
        logging.error(f"ERROR: Unexpected error loading surreal dictionary: {e}", exc_info=True)
        return None

# Cache the surreal dictionary (or defaults if loading failed)
surreal_dictionary = load_surreal_dictionary()

# Define defaults in case loading fails
DEFAULT_SURREAL_DATA = {
  "openers": [
    "Beneath the surface, a ripple murmurs:",
    "A forgotten sky hums:",
    "At the edge of thought, a whisper says:",
    "In the hollow between worlds, a voice lingers:",
    "Where light cannot reach, an echo flickers:"
  ],
  "themes": [
    "shattered mirrors",
    "burning snow",
    "breath of forgotten giants",
    "laughter stitched from starlight",
    "dreams carved from river stones"
  ],
  "symbols": [
    "cracked hourglass",
    "withered compass",
    "seed of a dying star",
    "pulse of the deep sea",
    "feather made of shadow"
  ]
}

def whisper_response(text):
    """Constructs a dynamically styled whisper response."""
    # Use loaded dictionary or fallback to defaults
    data_source = surreal_dictionary if surreal_dictionary else DEFAULT_SURREAL_DATA
    
    try:
        # Choose random elements safely
        opener = random.choice(data_source.get('openers', ["..."])) if data_source.get('openers') else "..."
        theme = random.choice(data_source.get('themes', ["unknown theme"])) if data_source.get('themes') else "unknown theme"
        symbol = random.choice(data_source.get('symbols', ["unknown symbol"])) if data_source.get('symbols') else "unknown symbol"

        # Build whispered output
        whispered_text = f"{opener} {text} (Dream Theme: {theme}, Symbol: {symbol})"
        return whispered_text
    except Exception as e:
        logging.error(f"Error generating whisper response: {e}", exc_info=True)
        # Fallback to a very basic response
        return f"[...] {text}"

# Example Usage (can be commented out)
# if __name__ == '__main__':
#     # Setup logging to see errors/info during testing
#     logging.basicConfig(level=logging.INFO)
#     print(whisper_response("Testing the dynamic whisper."))
#     print(whisper_response("Another thought emerges.")) 