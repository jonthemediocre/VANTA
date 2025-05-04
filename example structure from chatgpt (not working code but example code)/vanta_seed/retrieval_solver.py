# === retrieval_solver.py ===

"""
RetrievalSolver
Handles search and retrieval operations from knowledge bases.
"""

class RetrievalSolver:
    def __init__(self, config, memory_store):
        self.config = config
        self.memory_store = memory_store
        print("RetrievalSolver initialized.")

    def search(self, query):
        """
        Search memory store for query matches.
        """
        print(f"RetrievalSolver → Searching for → {query}")

        matches = []
        for key in self.memory_store.list_keys():
            record = self.memory_store.load(key)
            if query.lower() in str(record).lower():
                matches.append({"key": key, "record": record})

        print(f"RetrievalSolver → Found {len(matches)} matches.")
        return matches

    def fetch(self, key):
        """
        Fetch a specific record by key.
        """
        print(f"RetrievalSolver → Fetching → {key}")
        return self.memory_store.load(key)
