# vanta_seed/feedback/collector.py
import logging

try:
    # Attempt to import from the memory engine path
    from vanta_seed.memory.memory_engine import save_memory
except ImportError:
    logging.warning("FeedbackCollector could not import save_memory. Using dummy function.")
    # Define a dummy save_memory if the real one isn't available yet
    def save_memory(event_type, details):
        print(f"[Dummy Save] Event: {event_type}, Details: {details}")

class FeedbackCollector:
    def __init__(self, memory_engine=None):
        # Allow passing memory engine or use the imported function directly
        # This is slightly redundant if save_memory is globally imported,
        # but provides flexibility.
        self.mem_save = save_memory

    def collect(self, user_feedback, session_id):
        """Collects user feedback and saves it as a memory event."""
        record = {
            "feedback_text": user_feedback,
            "session_id": session_id
            # Consider adding timestamp here if not handled by save_memory
        }
        try:
            self.mem_save("user_feedback", record)
            logging.info(f"Saved feedback for session {session_id}")
        except Exception as e:
            logging.error(f"Failed to save feedback for session {session_id}: {e}") 