"""
VANTA Kernel - Universal Trigger Registry

This file defines the central registry for all protocol triggers used by the VANTA Kernel
and its connected applications (Guardian, InnerCircle, VantaChat, etc.).

The TriggerRegistry is a list of dictionaries, where each dictionary represents a
single trigger and its associated metadata and response routing.

Structure of a Trigger Dictionary:
- id (str): Unique identifier for the trigger (e.g., "tbri_throwing_object").
- trigger_type (str): The type of event that can activate this trigger 
  (e.g., "behavior_log", "context_change", "caregiver_request", "child_emotion_detected").
- match (dict): Specific criteria that the incoming event's payload must meet 
  for this trigger to be considered a match. Structure depends on trigger_type.
- module (str): The Python module (e.g., "vanta_protocols.tbri.throwing_response") 
  that contains the logic to execute when this trigger is activated.
  The VANTA Trigger Engine will dynamically import and call a known function 
  (e.g., `handle_trigger(event, child_profile, current_context)`)
  within this module.
- protocol (str): The overarching care protocol or framework this trigger belongs to 
  (e.g., "TBRI", "SafetyPlan", "EmotionRegulation", "NurturedHeartApproach").
- contexts (list[str]): A list of application contexts in which this trigger is active
  (e.g., ["guardian", "innercircle"]). If empty or null, implies global applicability (use with caution).
- metadata (dict, optional): Additional information like version, author, description.
"""

TriggerRegistry = [
    {
        "id": "tbri_throwing_object_v1",
        "trigger_type": "behavior_log", # Event comes from a behavior logging system
        "match": {
            "behavior_category": "aggression",
            "behavior_specific": "throwing_object",
            "intensity": ["medium", "high"] # Matches if intensity is medium OR high
        },
        "module": "vanta_protocols.tbri.throwing_response", # Path to the response logic module
        "protocol": "TBRI", # Trust-Based Relational Intervention
        "contexts": ["parent"], # Changed from ["guardian"]
        "metadata": {
            "version": "1.0",
            "description": "Handles incidents of a child throwing objects, based on TBRI principles.",
            "tags": ["aggression", "safety", "tbri"]
        }
    },
    {
        "id": "safetyplan_supervision_dogs_v1",
        "trigger_type": "child_context_change", # Event signifies a change in child's immediate context
        "match": {
            "context_variable": "supervision_level_dogs",
            "new_value": "unsupervised",
            "child_profile_tags": ["dog_safety_risk"] # Trigger if child has this tag
        },
        "module": "vanta_protocols.safety_plan.dog_supervision_alert",
        "protocol": "SafetyPlan",
        "contexts": ["parent", "social_worker"], # Changed from ["guardian", "innercircle"]
        "metadata": {
            "version": "1.0",
            "description": "Alerts caregivers if a child at risk around dogs is left unsupervised with them.",
            "tags": ["safety_plan", "animal_safety", "supervision"]
        }
    },
    # --- Placeholder for future triggers ---
    # {
    #     "id": "emotionregulation_escalation_detected_v1",
    #     "trigger_type": "child_emotion_stream",
    #     "match": {
    #         "dominant_emotion": "anger",
    #         "intensity_trend": "increasing_rapidly",
    #         "duration_seconds_gt": 60
    #     },
    #     "module": "vanta_protocols.emotion_regulation.deescalation_prompt",
    #     "protocol": "EmotionRegulation",
    #     "contexts": ["innercircle", "vantachat"],
    #     "metadata": {
    #         "version": "1.0",
    #         "description": "Offers de-escalation prompts when a child's anger is rapidly escalating.",
    #         "tags": ["emotion_regulation", "anger_management", "deescalation"]
    #     }
    # },
]

if __name__ == "__main__":
    # Example of how to access and print the registry (for testing/validation)
    print(f"Loaded {len(TriggerRegistry)} triggers from the VANTA Kernel Trigger Registry.")
    for i, trigger in enumerate(TriggerRegistry):
        print(f"\n--- Trigger {i+1} ---")
        print(f"  ID: {trigger.get('id')}")
        print(f"  Type: {trigger.get('trigger_type')}")
        print(f"  Protocol: {trigger.get('protocol')}")
        print(f"  Module: {trigger.get('module')}")
        print(f"  Contexts: {trigger.get('contexts')}")
        print(f"  Match Criteria: {trigger.get('match')}")
        if trigger.get('metadata'):
            print(f"  Description: {trigger['metadata'].get('description')}") 