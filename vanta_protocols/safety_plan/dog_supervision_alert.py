"""
Protocol Response Module for Safety Plan: Dog Supervision Alert
"""
import logging

# Standardized response format for the Visual Prompt Engine
VISUAL_PROMPT_TYPE = "visual_prompt"


def handle_trigger(event: dict, child_profile: dict, current_app_context: str, trigger_definition: dict) -> dict:
    """
    Handles a trigger related to a child needing supervision around dogs.

    Args:
        event (dict): The event payload that triggered this module.
        child_profile (dict): Profile data of the child involved.
        current_app_context (str): The current application context (e.g., "guardian").
        trigger_definition (dict): The definition of the trigger that was matched.

    Returns:
        dict: A response formatted for the Dynamic Visual Prompt Engine.
    """
    logging.info(f"Safety Plan Dog Supervision: Handling trigger '{trigger_definition.get('id')}' for event: {event.get('type')}")
    
    child_name = child_profile.get("name", "The child")
    # context_variable = event.get("context_variable") # e.g., "supervision_level_dogs"
    # new_value = event.get("new_value") # e.g., "unsupervised"

    message = f"Alert for {child_name}: Immediate supervision around dogs is required. Please ensure {child_name} is safe according to the safety plan."
    animation = "gentle_alert_attention" # Placeholder animation name
    emotions_to_acknowledge = ["concern", "safety_awareness"] # Potential emotions for caregiver

    if "dog_safety_risk" in child_profile.get("tags", []):
        message = f"Urgent: {child_name}, who has a dog safety risk, requires immediate supervision around dogs. Please check now and follow safety protocols."
        animation = "urgent_safety_alert"

    response = {
        "type": VISUAL_PROMPT_TYPE,
        "message": message,
        "animation": animation,
        "emotions": emotions_to_acknowledge, # These are more for caregiver context
        "protocol_applied": trigger_definition.get("protocol"),
        "trigger_id": trigger_definition.get("id")
    }

    logging.info(f"Safety Plan Dog Supervision: Generated response: {response}")
    return response

if __name__ == '__main__':
    print("Testing Safety Plan Dog Supervision Alert Module...")
    
    mock_event = {
        "type": "child_context_change",
        "context_variable": "supervision_level_dogs",
        "new_value": "unsupervised",
        "details": "Child entered area with dogs alone."
    }
    mock_child_profile_risk = {"name": "Bailey", "tags": ["dog_safety_risk"]}
    mock_child_profile_no_risk = {"name": "Casey", "tags": []}
    mock_trigger_def = {
        "id": "safetyplan_supervision_dogs_v1",
        "protocol": "SafetyPlan"
    }
    
    print("\n--- Test with child at risk ---")
    result_risk = handle_trigger(mock_event, mock_child_profile_risk, "guardian", mock_trigger_def)
    import json
    print(json.dumps(result_risk, indent=2))

    print("\n--- Test with child not specifically tagged at risk (general alert) ---")
    # This case might not be triggered if trigger_registry relies on child_profile_tags for matching.
    # However, the module itself can adapt its message if called.
    result_no_risk = handle_trigger(mock_event, mock_child_profile_no_risk, "innercircle", mock_trigger_def)
    print(json.dumps(result_no_risk, indent=2)) 