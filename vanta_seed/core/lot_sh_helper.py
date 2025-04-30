import logging
from typing import Dict, Optional, List # Added List for type hints if needed elsewhere
import ollama # Added

# --- LoT-Sh Helper Function (Moved from vanta_router_and_lora.py) ---

# Define constants for easier tuning
LOTSH_NARRATIVE_SNIPPET_LENGTH = 1000
LOTSH_CUE_TEMP = 0.1
LOTSH_MAP_TEMP = 0.2
LOTSH_EVAL_TEMP = 0.3 # Slightly higher for evaluation
LOTSH_PLAN_TEMP = 0.4 # Slightly higher for planning
LOTSH_MAX_TOKENS = 64 
LOTSH_MAX_CUE_LENGTH_RATIO = 0.75

# Define logger for this module
# logger = logging.getLogger(__name__) # Keep module level commented out or remove

async def extract_thought_hierarchy_shorthand(narrative: str, extraction_model: str, ollama_client: ollama.AsyncClient) -> Dict[str, Optional[str]]:
    """
    Generates a 4-step LoT-Sh dictionary using strict prompts.
    Accepts the Ollama client and extraction model name as arguments.
      T1_CUE: Extracted clue text.
      T2_MAP: Symbol mapped from the clue.
      T3_EVAL: Brief evaluation of symbol's relevance/potential.
      T4_PLAN: Concise next step/narrative direction.
    Returns None for values if steps fail.
    """
    import logging # Define logger locally
    logger = logging.getLogger(__name__)

    logger.debug(f"LOTSH: Using dedicated extraction model: {extraction_model}") # Uncommented
    
    shorthand_dict: Dict[str, Optional[str]] = {
        "T1_CUE": None, "T2_MAP": None, "T3_EVAL": None, "T4_PLAN": None
    }

    narrative_snippet = narrative[:LOTSH_NARRATIVE_SNIPPET_LENGTH] + ("..." if len(narrative) > LOTSH_NARRATIVE_SNIPPET_LENGTH else "")
    logger.debug(f"LOTSH: Processing snippet (first 100 chars): {narrative_snippet[:100]}") # Uncommented
    if not narrative_snippet.strip():
        logger.warning("LOTSH: Received empty narrative snippet.") # Uncommented
        return shorthand_dict # Return default dict with Nones

    # --- Step 1: CUE --- 
    cue_prompt = (
        "You are a Symbolic Distiller. Strictly follow these instructions:\n"
        "1. Read ONLY the following Text Snippet.\n"
        "2. Identify the single most significant and concise narrative clue, core image, or central feeling within it (max ~25 words).\n"
        "3. Do NOT use any information outside the provided 'Text Snippet'. Ignore all previous context.\n"
        "4. Output ONLY the exact text of the identified clue. No explanations, no quotes, no extra text, no newlines.\n\n"
        f"Text Snippet:\n'''\n{narrative_snippet}\n'''\n\n"
        "Output the single precise clue text ONLY:"
    )
    try:
        cue_options = {"temperature": LOTSH_CUE_TEMP, "num_predict": LOTSH_MAX_TOKENS, "stop": ["\n"]}
        logger.debug(f"LOTSH: Calling Ollama for CUE with model {extraction_model}") # Uncommented
        resp1 = await ollama_client.chat(model=extraction_model, messages=[{"role":"system","content":cue_prompt}], stream=False, options=cue_options)
        logger.debug(f"LOTSH: Raw CUE response: {resp1}") # Uncommented

        cue_text = resp1["message"]["content"].strip().strip('"').strip()
        logger.debug(f"LOTSH: Parsed cue_text: '{cue_text}'") # Uncommented

        if not cue_text or len(cue_text) > len(narrative_snippet) * LOTSH_MAX_CUE_LENGTH_RATIO:
             logger.warning(f"LOTSH: CUE step failed validation (empty or too long). Length: {len(cue_text)}, Snippet Length: {len(narrative_snippet)}") # Uncommented
             return shorthand_dict # Stop processing
        shorthand_dict["T1_CUE"] = cue_text

    except Exception as e:
        logger.error(f"LOTSH: Error during CUE step: {e}") # Uncommented
        return shorthand_dict # Stop processing

    # --- Step 2: MAP --- 
    map_prompt = (
         "You are a Symbolic Distiller. Strictly follow these instructions:\n"
         "1. Read ONLY the following Clue Text.\n"
         "2. Map this clue to a single, evocative, concise symbol or motif (1-4 words max).\n"
         "3. Do NOT use any information outside the provided 'Clue Text'. Ignore all previous context.\n"
         "4. Output ONLY the text of the symbol. No explanations, no quotes, no extra text, no newlines.\n\n"
         f"Clue Text:\n'''\n{cue_text}\n'''\n\n"
         "Output the single concise symbol ONLY:"
    )
    try:
        map_options = {"temperature": LOTSH_MAP_TEMP, "num_predict": LOTSH_MAX_TOKENS, "stop": ["\n"]}
        logger.debug(f"LOTSH: Calling Ollama for MAP with model {extraction_model}") # Uncommented
        resp2 = await ollama_client.chat(model=extraction_model, messages=[{"role":"system","content":map_prompt}], stream=False, options=map_options)
        logger.debug(f"LOTSH: Raw MAP response: {resp2}") # Uncommented

        mapped_symbol = resp2["message"]["content"].strip().lstrip('- ').strip().strip('"').strip()
        logger.debug(f"LOTSH: Parsed mapped_symbol: '{mapped_symbol}'") # Uncommented

        if not mapped_symbol:
             logger.warning("LOTSH: MAP step returned empty.") # Uncommented
             return shorthand_dict # Return T1 only
        shorthand_dict["T2_MAP"] = mapped_symbol

    except Exception as e:
        logger.error(f"LOTSH: Error during MAP step: {e}") # Uncommented
        return shorthand_dict # Return T1 only
        
    # --- Step 3: EVAL --- 
    eval_prompt = (
        "You are a Narrative Evaluator. Strictly follow these instructions:\n"
        "1. Consider the following Clue and its mapped Symbol.\n"
        "2. Briefly evaluate the symbol's relevance or potential impact on the narrative (1 sentence max).\n"
        "3. Output ONLY the evaluation sentence. No explanations, no quotes, no extra text, no newlines.\n\n"
        f"Clue Text:\n'''\n{cue_text}\n'''\n"
        f"Mapped Symbol:\n'''\n{mapped_symbol}\n'''\n\n"
        "Output the single evaluation sentence ONLY:"
    )
    try:
        eval_options = {"temperature": LOTSH_EVAL_TEMP, "num_predict": LOTSH_MAX_TOKENS, "stop": ["\n"]}
        logger.debug(f"LOTSH: Calling Ollama for EVAL with model {extraction_model}") # Uncommented
        resp3 = await ollama_client.chat(model=extraction_model, messages=[{"role":"system","content":eval_prompt}], stream=False, options=eval_options)
        logger.debug(f"LOTSH: Raw EVAL response: {resp3}") # Uncommented
        
        evaluation_text = resp3["message"]["content"].strip().strip('"').strip()
        logger.debug(f"LOTSH: Parsed evaluation_text: '{evaluation_text}'") # Uncommented

        if not evaluation_text:
             logger.warning("LOTSH: EVAL step returned empty.") # Uncommented
             return shorthand_dict # Stop processing
        shorthand_dict["T3_EVAL"] = evaluation_text

    except Exception as e:
        logger.error(f"LOTSH: Error during EVAL step: {e}") # Uncommented
        return shorthand_dict # Stop processing
        
    # --- Step 4: PLAN --- 
    plan_prompt = (
        "You are a Narrative Planner. Strictly follow these instructions:\n"
        "1. Consider the Clue, Symbol, and Evaluation.\n"
        "2. Suggest a concise next step or direction for the narrative (max 10 words).\n"
        "3. Output ONLY the plan text. No explanations, no quotes, no extra text, no newlines.\n\n"
        f"Clue Text:\n'''\n{cue_text}\n'''\n"
        f"Mapped Symbol:\n'''\n{mapped_symbol}\n'''\n"
        f"Evaluation:\n'''\n{shorthand_dict.get('T3_EVAL', 'N/A')}\n'''\n\n"
        "Output the concise plan ONLY:"
    )
    try:
        plan_options = {"temperature": LOTSH_PLAN_TEMP, "num_predict": LOTSH_MAX_TOKENS, "stop": ["\n"]}
        logger.debug(f"LOTSH: Calling Ollama for PLAN with model {extraction_model}") # Uncommented
        resp4 = await ollama_client.chat(model=extraction_model, messages=[{"role":"system","content":plan_prompt}], stream=False, options=plan_options)
        logger.debug(f"LOTSH: Raw PLAN response: {resp4}") # Uncommented

        plan_text = resp4["message"]["content"].strip().strip('"').strip()
        logger.debug(f"LOTSH: Parsed plan_text: '{plan_text}'") # Uncommented

        if not plan_text:
             logger.warning("LOTSH: PLAN step returned empty.") # Uncommented
             return shorthand_dict # Stop processing
        shorthand_dict["T4_PLAN"] = plan_text

    except Exception as e:
        logger.error(f"LOTSH: Error during PLAN step: {e}") # Uncommented
        return shorthand_dict # Stop processing

    logger.debug(f"LOTSH: Final shorthand dict: {shorthand_dict}") # Uncommented
    return shorthand_dict 