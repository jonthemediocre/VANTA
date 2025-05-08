"""
VANTA Kernel - Universal Trigger Engine

This engine processes incoming events against the TriggerRegistry, dynamically
executing the appropriate response module when a match is found.
"""
import importlib
import logging
from trigger_registry import TriggerRegistry # Assuming trigger_registry.py is in the same directory or PYTHONPATH

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class VantaTriggerEngine:
    def __init__(self):
        self.registry = TriggerRegistry
        if not self.registry:
            logging.warning("TriggerRegistry is empty. The engine will not process any triggers.")

    def _matches(self, match_criteria: dict, event_payload: dict) -> bool:
        """Deeply checks if the event_payload satisfies all match_criteria."""
        if not isinstance(match_criteria, dict) or not isinstance(event_payload, dict):
            logging.debug(f"Match criteria or event payload is not a dict. Criteria: {match_criteria}, Payload: {event_payload}")
            return False

        for key, expected_value in match_criteria.items():
            actual_value = event_payload.get(key)

            if actual_value is None and expected_value is not None:
                logging.debug(f"Key '{key}' not found in event_payload or is None.")
                return False

            if isinstance(expected_value, list):
                # If expected is a list, actual must be in that list
                if actual_value not in expected_value:
                    logging.debug(f"Key '{key}': '{actual_value}' not in expected list {expected_value}.")
                    return False
            elif isinstance(expected_value, dict):
                # If expected is a dict, recursively check nested criteria
                if not isinstance(actual_value, dict) or not self._matches(expected_value, actual_value):
                    logging.debug(f"Key '{key}': Nested criteria mismatch for {expected_value} and {actual_value}.")
                    return False
            else:
                # Simple value comparison
                if actual_value != expected_value:
                    logging.debug(f"Key '{key}': '{actual_value}' != '{expected_value}'.")
                    return False
        return True

    def process_event(self, event: dict, current_app_context: str, child_profile: dict = None) -> dict | None:
        """
        Processes an incoming event and executes the first matched trigger's module.

        Args:
            event (dict): The event payload. Must contain a "type" key corresponding
                          to trigger_type in the registry, and other data for matching.
            current_app_context (str): The current application context (e.g., "guardian").
            child_profile (dict, optional): Profile data of the child involved.

        Returns:
            dict | None: The result from the executed trigger module, or None if no trigger matches.
        """
        if not self.registry:
            logging.info("No triggers in registry to process.")
            return None
        
        event_type = event.get("type")
        if not event_type:
            logging.warning("Event is missing 'type' key. Cannot process.")
            return None

        logging.info(f"Processing event of type '{event_type}' for context '{current_app_context}'.")

        for trigger_definition in self.registry:
            # 1. Check trigger_type
            if trigger_definition.get("trigger_type") != event_type:
                continue

            # 2. Check app context
            allowed_contexts = trigger_definition.get("contexts", [])
            if allowed_contexts and current_app_context not in allowed_contexts:
                logging.debug(f"Trigger '{trigger_definition.get('id')}' skipped: context '{current_app_context}' not in {allowed_contexts}.")
                continue

            # 3. Check match criteria
            if self._matches(trigger_definition.get("match", {}), event.get("payload", event)):
                logging.info(f"Event matched trigger: {trigger_definition.get('id')}")
                module_name = trigger_definition.get("module")
                if not module_name:
                    logging.error(f"Trigger '{trigger_definition.get('id')}' matched but has no module defined.")
                    continue
                
                try:
                    # Dynamically import the module
                    # Assuming modules are in a package structure that can be imported
                    # e.g., if module is "vanta_protocols.tbri.throwing_response", it will try to import that.
                    # Ensure your PYTHONPATH is set up correctly or these modules are in an installable package.
                    response_module = importlib.import_module(module_name)
                    
                    # Call a standardized handler function within the module
                    if hasattr(response_module, "handle_trigger"):
                        logging.info(f"Executing module: {module_name}.handle_trigger")
                        # Pass relevant parts of the event or the whole event as needed
                        return response_module.handle_trigger(event, child_profile, current_app_context, trigger_definition)
                    else:
                        logging.error(f"Module {module_name} does not have a 'handle_trigger' function.")
                        return {"error": f"Handler not found in module {module_name}"}
                except ImportError as e:
                    logging.error(f"Failed to import module {module_name} for trigger '{trigger_definition.get('id')}': {e}")
                    return {"error": f"Module {module_name} not found or import error."}
                except Exception as e:
                    logging.error(f"Error executing module {module_name} for trigger '{trigger_definition.get('id')}': {e}")
                    return {"error": f"Error in module {module_name}: {str(e)}"}
            else:
                logging.debug(f"Event did not match criteria for trigger: {trigger_definition.get('id')}")

        logging.info("No matching trigger found for the event.")
        return None

if __name__ == "__main__":
    print("VANTA Trigger Engine - Basic Test Run (Using Actual Modules)")
    engine = VantaTriggerEngine()

    # NOTE: For the following tests to work with actual modules,
    # this script (vanta_trigger_engine.py) should ideally be run
    # from the root of the VANTA project directory, or the
    # VANTA project root must be in the PYTHONPATH so that
    # "vanta_protocols.tbri.throwing_response" etc. can be imported.
    #
    # Example execution from VANTA project root:
    # python vanta_trigger_engine.py
    # OR
    # PYTHONPATH=. python vanta_trigger_engine.py

    # Test Case 1: Matching TBRI trigger
    print("\n--- Test Case 1: TBRI Throwing Object ---")
    # Adjusting event1 to match flat structure for this test (matching trigger_registry.py example)
    flat_event1 = {
        "type": "behavior_log",
        "behavior_category": "aggression",
        "behavior_specific": "throwing_object",
        "intensity": "high",
        "details": "Child threw a toy car at the wall."
    }
    result1 = engine.process_event(flat_event1, "guardian", child_profile={"name": "Test Child A"})
    print(f"Result 1: {result1}")

    # Test Case 2: Matching SafetyPlan trigger
    print("\n--- Test Case 2: Safety Plan Dog Supervision ---")
    event2 = {
        "type": "child_context_change",
        "context_variable": "supervision_level_dogs",
        "new_value": "unsupervised",
        "child_profile_tags": ["dog_safety_risk"], 
        "details": "Child is now alone in the backyard where dogs are present."
    }
    result2 = engine.process_event(event2, "innercircle", child_profile={"name": "Test Child B", "tags":["dog_safety_risk"] })
    print(f"Result 2: {result2}")

    # Test Case 3: No matching trigger type
    print("\n--- Test Case 3: Unmatched Event Type ---")
    event3 = {"type": "caregiver_request", "request": "Suggest dinner ideas."}
    result3 = engine.process_event(event3, "guardian")
    print(f"Result 3: {result3}")

    # Test Case 4: Matching type but not criteria
    print("\n--- Test Case 4: Matched Type, Unmatched Criteria ---")
    event4 = {
        "type": "behavior_log",
        "behavior_category": "play", 
        "behavior_specific": "sharing_toy",
        "intensity": "low"
    }
    result4 = engine.process_event(event4, "guardian")
    print(f"Result 4: {result4}")

    # Test Case 5: Context mismatch
    print("\n--- Test Case 5: Context Mismatch ---")
    result5 = engine.process_event(flat_event1, "vantachat") 
    print(f"Result 5: {result5}")

    # Test Case 6: Trigger with undefined module (example, if one was in registry)
    # To test this, you'd add a trigger to trigger_registry.py with a non-existent module name.
    # And then create an event that matches it.
    # print("\n--- Test Case 6: Undefined Module ---")
    # event_undefined_module = {"type": "test_undefined_module_type", "module_should_be": "non_existent_module.handler"}
    # # Ensure trigger_registry.py has a trigger that would match this event and point to "non_existent_module.handler"
    # result6 = engine.process_event(event_undefined_module, "guardian")
    # print(f"Result 6: {result6}")

    # Test Case 7: Event payload is nested (ensure _matches and process_event handle event.get(\"payload\" correctly)
    print("\n--- Test Case 7: TBRI Throwing Object (Event with 'payload' key) ---")
    event_with_payload = {
        "type": "behavior_log",
        "payload": {
            "behavior_category": "aggression",
            "behavior_specific": "throwing_object",
            "intensity": "medium",
            "details": "Child threw a soft ball."
        }
    }
    # The VantaTriggerEngine's process_event uses event.get("payload", event) for _matches,
    # so this should work if the match criteria in trigger_registry.py are flat.
    # If match criteria were also nested, _matches would handle it.
    result7 = engine.process_event(event_with_payload, "guardian", child_profile={"name": "Test Child C"})
    print(f"Result 7: {result7}") 