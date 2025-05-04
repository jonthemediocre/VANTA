# === episodic_memory.py ===

"""
EpisodicMemory
Records and retrieves sequential events for context and history.
"""

import datetime

class EpisodicMemory:
    def __init__(self, config, memory_store):
        self.config = config
        self.store = memory_store
        self.max_episodes = config.get_nested('episodic_memory', 'max_episodes', 1000)
        self.episode_key_prefix = "episode_"
        print("EpisodicMemory initialized.")

    def initialize(self):
        """
        Initialize episodic memory (placeholder for future expansion).
        """
        print("EpisodicMemory → Initialized.")

    def record_event(self, event_type, data):
        """
        Record an event with timestamp.
        """
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        episode_id = f"{self.episode_key_prefix}{timestamp}_{event_type}"

        event_record = {
            'timestamp': timestamp,
            'event_type': event_type,
            'data': data
        }

        print(f"EpisodicMemory → Recording event → {event_type} → ID: {episode_id}")

        self.store.save(episode_id, event_record)

    def retrieve_recent(self, limit=10):
        """
        Retrieve recent events (most recent first).
        """
        print(f"EpisodicMemory → Retrieving last {limit} events.")
        all_event_keys = sorted([k for k in self.store.store.keys() if k.startswith(self.episode_key_prefix)], reverse=True)
        recent_keys = all_event_keys[:limit]
        return [self.store.load(k) for k in recent_keys]

    def search_events(self, query_term):
        """
        Search recorded events for a term.
        """
        print(f"EpisodicMemory → Searching events for → {query_term}")
        all_events = [self.store.load(k) for k in self.store.store.keys() if k.startswith(self.episode_key_prefix)]

        results = [
            event for event in all_events
            if query_term in event.get("event_type", "") or query_term in str(event.get("data", ""))
        ]

        print(f"EpisodicMemory → Found {len(results)} matching events.")
        return results
