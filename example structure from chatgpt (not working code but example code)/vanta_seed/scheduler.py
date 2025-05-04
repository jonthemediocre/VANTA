# === scheduler.py ===

"""
Scheduler
Handles scheduling and execution of periodic or delayed tasks.
"""

import threading
import time
import datetime

class Scheduler:
    def __init__(self, config):
        self.config = config
        self.tasks = []
        self._stop_event = threading.Event()
        self._thread = None
        print("Scheduler initialized.")

    def schedule_task(self, task_fn, delay_seconds):
        """
        Schedule a task to run after delay.
        """
        run_at = datetime.datetime.now() + datetime.timedelta(seconds=delay_seconds)
        self.tasks.append((run_at, task_fn))
        print(f"Scheduler → Task scheduled at {run_at}.")

    def _run(self):
        print("Scheduler → Background loop started.")
        while not self._stop_event.is_set():
            now = datetime.datetime.now()
            for task in list(self.tasks):
                run_at, task_fn = task
                if now >= run_at:
                    print("Scheduler → Executing scheduled task.")
                    try:
                        task_fn()
                    except Exception as e:
                        print(f"Scheduler → Task error → {e}")
                    self.tasks.remove(task)

            time.sleep(1)

        print("Scheduler → Background loop stopped.")

    def start(self):
        if self._thread and self._thread.is_alive():
            return  # Already running

        print("Scheduler → Starting scheduler thread.")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        print("Scheduler → Stopping scheduler thread.")
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._thread = None

    def shutdown(self):
        self.stop()
