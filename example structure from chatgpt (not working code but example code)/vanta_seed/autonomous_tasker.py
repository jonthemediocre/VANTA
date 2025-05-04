# === autonomous_tasker.py ===

"""
AutonomousTasker
Handles background autonomous tasks execution.
"""

import threading
import time

class AutonomousTasker:
    def __init__(self, config, automutator):
        self.config = config
        self.automutator = automutator
        self.enabled = self.config.get_nested("autonomous_tasker", "enabled", default=False)
        self._stop_event = threading.Event()
        self._thread = None
        print(f"AutonomousTasker initialized. Enabled: {self.enabled}")

    def _task_loop(self):
        print("AutonomousTasker → Background task loop started.")
        while not self._stop_event.is_set():
            print("AutonomousTasker → Checking for autonomous tasks (placeholder logic)...")

            # Example → evaluate self-maintenance mutation trigger
            if self.automutator:
                self.automutator.evaluate_mutation("routine_check")

            interval = self.config.get_nested("autonomous_tasker", "check_interval_seconds", default=300)
            self._stop_event.wait(interval)

        print("AutonomousTasker → Background task loop stopped.")

    def start(self):
        if self.enabled:
            print("AutonomousTasker → Starting background thread.")
            if self._thread is None or not self._thread.is_alive():
                self._stop_event.clear()
                self._thread = threading.Thread(target=self._task_loop, daemon=True)
                self._thread.start()
        else:
            print("AutonomousTasker → Disabled in configuration.")

    def stop(self):
        if self._thread and self._thread.is_alive():
            print("AutonomousTasker → Stopping background thread...")
            self._stop_event.set()
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                print("AutonomousTasker → ⚠️ Thread did not stop gracefully.")
            else:
                print("AutonomousTasker → Thread stopped.")
        self._thread = None

    def shutdown(self):
        self.stop()
