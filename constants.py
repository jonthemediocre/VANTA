"""
Defines constant values used across the VANTA framework, such as standard intents.
"""

# --- Standard Task Intents ---
GENERATE_IMAGE = "generate_image"
GENERATE_SPEECH = "generate_speech"
GENERATE_DIALOGUE = "generate_dialogue"
REFLECT_ON_MEMORY = "reflect_on_memory"

# --- Suggestion/Action Related Intents ---
# Example intents for acting on suggestions from other agents
APPLY_REFACTORING_SUGGESTION = "apply_refactoring_suggestion"
APPLY_MUTATION_SUGGESTION = "apply_mutation_suggestion"
LOG_PATTERN_SUGGESTION = "log_pattern_suggestion"
REVIEW_PROMPT_TEMPLATE = "review_prompt_template" # From ReflectorAgent example

# --- Scheduled Task Intents (Example) ---
# Convention: prefix with SCHEDULED_ for clarity
SCHEDULED_MEMORY_CLEANUP = "scheduled_memory_cleanup"
SCHEDULED_SYSTEM_HEALTH_CHECK = "scheduled_system_health_check"

# Add other constants like default model names, file paths etc. here if desired 