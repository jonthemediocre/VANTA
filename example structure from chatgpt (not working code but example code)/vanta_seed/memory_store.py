# === memory_store.py ===

"""
MemoryStore
Simple in-memory key-value storage system.
"""

import os
import yaml

class MemoryStore:
    def __init__(self, storage_file_path=None):
        self.storage_file = storage_file_path or "memory_store.yaml"
        self.store = {}
        print("MemoryStore initialized.")

    def load_store(self):
        if not os.path.exists(self.storage_file):
            print("MemoryStore → No store file found. Starting fresh.")
            self.store = {}
            return

        try:
            with open(self.storage_file, 'r') as f:
                self.store = yaml.safe_load(f) or {}
            print("MemoryStore → Store loaded.")
        except Exception as e:
            print(f"MemoryStore → Error loading store → {e}")
            self.store = {}

    def save_store(self):
        try:
            with open(self.storage_file, 'w') as f:
                yaml.safe_dump(self.store, f)
            print("MemoryStore → Store saved.")
        except Exception as e:
            print(f"MemoryStore → Error saving store → {e}")

    def save(self, key, value):
        self.store[key] = value
        self.save_store()

    def load(self, key):
        return self.store.get(key)

    def delete(self, key):
        if key in self.store:
            del self.store[key]
            self.save_store()

    def list_keys(self):
        return list(self.store.keys())
