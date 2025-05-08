"""
Protocol Response Module for TBRI: Handling Throwing Objects

Applies Trust-Based Relational Intervention (TBRI) principles (Connect, Empower, Correct)
when responding to events where a child is throwing objects.
"""
import logging

# Standardized response format for the Visual Prompt Engine
VISUAL_PROMPT_TYPE = "visual_prompt"


def _get_connection_message(intensity: str, child_name: str) -> tuple[str, str, list]:
    """Helper to determine initial connection message based on intensity."""
    if intensity == "low":
        message = f"{child_name}, I see you might be feeling frustrated or need something. Throwing isn't the safest way, but I'm here to understand. Can we talk?"
        animation = "gentle_approach_questioning"
        emotions = ["calm", "empathetic", "curious"]
    elif intensity == "medium":
        message = f"{child_name}, throwing things tells me you have some big feelings right now. That must be tough. Let's take a moment together to find a safer way to feel better."
        animation = "calm_down_invitation"
        emotions = ["concerned", "calm", "supportive"]
    elif intensity == "high":
        message = f"{child_name}, throwing things isn't safe. I need to make sure everyone stays safe right now. I'm right here with you while things calm down."
        animation = "safety_presence_calm"
        emotions = ["firm", "calm", "protective"]
    else: # Unknown or other intensity
        message = f"{child_name}, I notice something was thrown. I'm here to help figure out what's going on."
        animation = "neutral_observe_approach"
        emotions = ["neutral", "observant"]
    return message, animation, emotions

def _get_empowerment_suggestion(calming_strategies: list) -> str | None:
    """Helper to suggest a known calming strategy."""
    if calming_strategies:
        strategy = calming_strategies[0] # Suggest first known strategy
        # Could be randomized or context-based later
        return f" Would you like to try {strategy} to help your body feel calmer?"
    return None

def _get_correction_component(intensity: str) -> str | None:
    """Helper to add a gentle corrective/teaching component (used carefully)."""
    # Correction is often the last step, after connection and safety
    if intensity in ["medium", "high"]:
        return " Once things are calm, we can talk about safe ways to show big feelings."
    elif intensity == "low":
         return " Let's think of another way to let me know what you need next time."
    return None

def handle_trigger(event: dict, child_profile: dict, current_app_context: str, trigger_definition: dict) -> dict:
    """
    Handles a trigger related to a child throwing objects, based on TBRI principles.
    Prioritizes Connection, then offers Empowerment/Correction based on intensity.

    Args:
        event (dict): The event payload that triggered this module.
        child_profile (dict): Profile data of the child involved.
        current_app_context (str): The current application context (e.g., "guardian").
        trigger_definition (dict): The definition of the trigger that was matched.

    Returns:
        dict: A response formatted for the Dynamic Visual Prompt Engine.
    """
    logging.info(f"TBRI Throwing Response: Handling trigger '{trigger_definition.get('id')}' for event type: {event.get('type')}")
    
    child_name = child_profile.get("name", "the child")
    # Ensure intensity is read from the event, not the trigger definition's match criteria
    intensity = event.get("intensity", "unknown").lower()
    # Get profile data, defaulting to empty lists if not present
    known_triggers = child_profile.get("known_triggers", [])
    calming_strategies = child_profile.get("preferred_calming_strategies", [])

    logging.debug(f"  Child: {child_name}, Intensity: {intensity}, Context: {current_app_context}")
    logging.debug(f"  Known Triggers: {known_triggers}, Preferred Strategies: {calming_strategies}")

    # 1. Connect (Primary Message)
    message, animation, emotions = _get_connection_message(intensity, child_name)

    # 2. Empower (Offer Choices/Strategies)
    empowerment_suggestion = _get_empowerment_suggestion(calming_strategies)
    if empowerment_suggestion:
        message += empowerment_suggestion
        # Potentially adjust animation/emotions if empowerment offered
        animation += "_with_choice" 

    # 3. Correct (Gentle Teaching - Optional, after calm)
    correction_component = _get_correction_component(intensity)
    if correction_component:
        # Append correction subtly, maybe as a separate thought or follow-up cue
        # For now, just append to message for simplicity
        message += correction_component 

    # Constructing the response based on the Dynamic Visual Prompt Engine schema
    response = {
        "type": VISUAL_PROMPT_TYPE,
        "message": message,
        "animation": animation, # Placeholder animation name needs mapping to actual assets
        "emotions": emotions, # Represents the desired caregiver emotion/tone
        "protocol_applied": trigger_definition.get("protocol", "TBRI"), # Get from trigger def
        "trigger_id": trigger_definition.get("id")
    }

    logging.info(f"TBRI Throwing Response: Generated response for trigger '{response['trigger_id']}': Type={response['type']}")
    return response

# Example use case (for testing this module directly)
if __name__ == '__main__':
    print("Testing Enhanced TBRI Throwing Response Module...")
    
    # Mock Trigger Definition (as passed by engine)
    mock_trigger_def = {
        "id": "tbri_throwing_object_v1",
        "protocol": "TBRI",
        # other fields from registry...
    }
    
    # Mock Child Profiles
    child_alex = {"name": "Alex", "known_triggers": ["transitions"], "preferred_calming_strategies": ["deep breathing", "using a fidget toy"]}
    child_sam = {"name": "Sam"} # No specific profile data
    
    # Test Cases
    test_events = [
        {"type": "behavior_log", "intensity": "high", "details": "threw a book hard"},
        {"type": "behavior_log", "intensity": "medium", "details": "tossed a stuffed animal"},
        {"type": "behavior_log", "intensity": "low", "details": "dropped a crayon angrily"},
        {"type": "behavior_log", "intensity": "unknown", "details": "something was thrown"}
    ]
    
    import json
    
    print("\n--- Testing with Child Alex (has profile data) ---")
    for i, event in enumerate(test_events):
        print(f"\nTest {i+1} (Intensity: {event['intensity']}):")
        result = handle_trigger(event, child_alex, "guardian", mock_trigger_def)
        print(json.dumps(result, indent=2))
        
    print("\n--- Testing with Child Sam (no profile data) ---")
    for i, event in enumerate(test_events):
        print(f"\nTest {i+1} (Intensity: {event['intensity']}):")
        result = handle_trigger(event, child_sam, "guardian", mock_trigger_def)
        print(json.dumps(result, indent=2)) 