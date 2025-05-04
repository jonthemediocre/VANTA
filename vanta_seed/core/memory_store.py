import logging
from typing import List, Dict, Any, Optional
from collections import deque
import time
import json # For simple search
import os
import yaml # <<< ADDED: Import yaml

logger = logging.getLogger(__name__)

class MemoryStore:
    """
    Simple in-memory store for agent memories and symbolic data.
    Uses a deque for efficient appending and limiting size.
    Optionally persists to a YAML file.
    """
    # --- Define default path relative to this file --- 
    # Adjust as needed if project structure changes
    DEFAULT_PERSIST_DIR = os.path.join(os.path.dirname(__file__), '..', 'memory') 
    DEFAULT_PERSIST_FILE = "memory_items.yaml"
    # -------------------------------------------------

    def __init__(self, max_items: int = 10000, persist_path: Optional[str] = None):
        self.max_items = max_items
        self._memory_log: deque[Dict[str, Any]] = deque(maxlen=max_items)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # --- Set Persistence Path --- 
        if persist_path:
            self.persist_path = persist_path
        else:
            # Ensure the default directory exists
            os.makedirs(self.DEFAULT_PERSIST_DIR, exist_ok=True)
            self.persist_path = os.path.join(self.DEFAULT_PERSIST_DIR, self.DEFAULT_PERSIST_FILE)
        self.logger.info(f"MemoryStore persistence path set to: {self.persist_path}")
        # --------------------------
        
        # --- Load existing data --- 
        self._load_from_yaml()
        # --------------------------
        
        self.logger.info(f"MemoryStore initialized. Current size: {len(self._memory_log)}, Max items: {max_items}.")

    def _load_from_yaml(self):
        """Loads memory items from the YAML file on initialization."""
        if not self.persist_path or not os.path.exists(self.persist_path):
            self.logger.info(f"Persistence file not found at {self.persist_path}. Starting with empty memory.")
            return
            
        try:
            with open(self.persist_path, 'r') as f:
                loaded_items = yaml.safe_load(f)
                if isinstance(loaded_items, list):
                    # Validate basic structure if needed (optional)
                    valid_items = [item for item in loaded_items if isinstance(item, dict) and 'timestamp' in item]
                    
                    # Sort by timestamp to load in chronological order
                    valid_items.sort(key=lambda x: x.get('timestamp', 0))
                    
                    # Add to deque, respecting maxlen (oldest loaded first)
                    # If loaded > maxlen, only the most recent maxlen items will be kept by deque
                    for item in valid_items:
                         self._memory_log.append(item) 
                         
                    self.logger.info(f"Loaded {len(valid_items)} items from {self.persist_path}. Deque size: {len(self._memory_log)}")
                elif loaded_items is None: # Empty file
                     self.logger.info(f"Persistence file {self.persist_path} is empty.")
                else:
                    self.logger.warning(f"Persistence file {self.persist_path} does not contain a list. Ignoring content.")
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML from {self.persist_path}: {e}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Error loading memory from {self.persist_path}: {e}", exc_info=True)

    def _save_to_yaml(self):
        """Saves the current memory log to the YAML file."""
        if not self.persist_path:
            self.logger.warning("Cannot save memory, persist_path not set.")
            return False
            
        try:
            # Convert deque to list for serialization
            items_to_save = list(self._memory_log)
            with open(self.persist_path, 'w') as f:
                yaml.dump(items_to_save, f, default_flow_style=False, sort_keys=False)
            self.logger.debug(f"Successfully saved {len(items_to_save)} memory items to {self.persist_path}.")
            return True
        except Exception as e:
            self.logger.error(f"Error saving memory to {self.persist_path}: {e}", exc_info=True)
            return False

    # --- ADDED: Explicit save method --- 
    def save(self) -> bool:
        """Explicitly triggers saving the current memory state to YAML."""
        return self._save_to_yaml()
    # ----------------------------------

    def add_item(self, agent_id: str, type: str, content: dict, tags: Optional[List[str]] = None) -> bool:
        """Adds a new item to the memory log, optionally including tags."""
        if not isinstance(content, dict):
            self.logger.error(f"Memory item content must be a dictionary, received: {type(content)}")
            return False
        
        timestamp = time.time()
        item = {
            "agent_id": agent_id,
            "type": type,
            "content": content,
            "tags": tags or [],
            "timestamp": timestamp
        }
        
        try:
            # Deque automatically handles maxlen constraint by removing oldest items
            self._memory_log.append(item)
            # --- Defer saving to a separate method or trigger --- 
            # self._save_to_yaml() # <<< COMMENTED OUT for now - save explicitly or periodically
            self.logger.debug(f"Added memory item for agent '{agent_id}', type '{type}', tags {item['tags']}. Current size: {len(self._memory_log)}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add item to memory log: {e}", exc_info=True)
            return False

    def get_items_simple(self, agent_id: Optional[str] = None, type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves the most recent items, optionally filtered by agent_id and/or type (simple version)."""
        
        # Since deque stores items chronologically (oldest to newest),
        # we iterate in reverse to get the most recent items first.
        
        results = []
        count = 0
        
        # Iterate from right (newest) to left (oldest)
        for item in reversed(self._memory_log):
            if count >= limit:
                break
                
            matches_agent = agent_id is None or item.get("agent_id") == agent_id
            matches_type = type is None or item.get("type") == type
            
            if matches_agent and matches_type:
                results.append(item)
                count += 1
                
        self.logger.debug(f"Retrieved {len(results)} items matching agent='{agent_id}', type='{type}', limit={limit}.")
        # The results are already in newest-to-oldest order due to reversed iteration
        return results

    # --- REVISED get_items with advanced filtering --- 
    def get_items_filtered(
        self,
        agent_id: Optional[str] = None,
        type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Retrieves the most recent items with advanced filtering.

        Args:
            agent_id: Filter by agent ID.
            type: Filter by item type.
            tags: Filter by items containing ALL specified tags (list intersection).
            start_time: Filter items with timestamp >= start_time.
            end_time: Filter items with timestamp <= end_time.
            limit: Maximum number of items to return.
        """
        results = []
        count = 0
        required_tags_set = set(tags) if tags else set()

        for item in reversed(self._memory_log):
            if count >= limit:
                break

            # Perform filtering checks
            matches_agent = agent_id is None or item.get("agent_id") == agent_id
            matches_type = type is None or item.get("type") == type
            matches_start_time = start_time is None or item.get("timestamp", 0) >= start_time
            matches_end_time = end_time is None or item.get("timestamp", 0) <= end_time
            
            # Tag matching: check if all required tags are present in the item's tags
            item_tags_set = set(item.get("tags", []))
            matches_tags = required_tags_set.issubset(item_tags_set)

            if matches_agent and matches_type and matches_start_time and matches_end_time and matches_tags:
                results.append(item)
                count += 1

        self.logger.debug(f"Retrieved {len(results)} items matching filters (agent='{agent_id}', type='{type}', tags={tags}, start={start_time}, end={end_time}, limit={limit}).")
        return results
    # -----------------------------------------------

    def search_items(self, query: str, agent_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Performs a very basic case-insensitive search within the 'content' dictionary 
        of memory items, optionally filtered by agent_id.
        This is NOT a sophisticated search, just a simple substring check.
        """
        results = []
        count = 0
        query_lower = query.lower()
        
        for item in reversed(self._memory_log):
            if count >= limit:
                break
            
            matches_agent = agent_id is None or item.get("agent_id") == agent_id
            
            if matches_agent:
                # Basic search: serialize content to JSON and check if query substring exists
                try:
                    content_str = json.dumps(item.get("content", {})).lower()
                    if query_lower in content_str:
                        results.append(item)
                        count += 1
                except Exception as e:
                    self.logger.warning(f"Could not serialize content for search in item from agent {item.get('agent_id')}: {e}")
        
        self.logger.debug(f"Found {len(results)} items via basic search for query='{query}' matching agent='{agent_id}', limit={limit}.")
        return results

    def get_store_size(self) -> int:
        """Returns the current number of items in the memory store."""
        return len(self._memory_log)

# Example usage (can be removed or placed in tests)
if __name__ == '__main__':
    store = MemoryStore(max_items=5)
    store.add_item("agent1", "narrative", {"text": "Event A happened"})
    time.sleep(0.1)
    store.add_item("agent2", "ritual_log", {"ritual": "init", "status": "success"})
    time.sleep(0.1)
    store.add_item("agent1", "narrative", {"text": "Event B followed A"})
    time.sleep(0.1)
    store.add_item("agent1", "mutation", {"target": "state", "change": "increase"})
    time.sleep(0.1)
    store.add_item("agent2", "narrative", {"text": "Meanwhile, agent2 observed Event C"})
    
    print("--- All Items (Newest First) ---")
    print(json.dumps(store.get_items_simple(limit=10), indent=2))
    
    print("\n--- Agent1 Items (Limit 2) ---")
    print(json.dumps(store.get_items_simple(agent_id="agent1", limit=2), indent=2))
    
    print("\n--- Narrative Type Items (Limit 2) ---")
    print(json.dumps(store.get_items_simple(type="narrative", limit=2), indent=2))
    
    print("\n--- Search for 'event' ---")
    print(json.dumps(store.search_items(query="event", limit=10), indent=2))

    # Test max_items limit
    store.add_item("agent3", "agent_state", {"energy": 0.5}) 
    print(f"\n--- Store size after adding 6th item (max=5): {store.get_store_size()} ---")
    print("First item (oldest) should be Event A, check if it's gone:")
    print(json.dumps(store.get_items_simple(limit=10), indent=2)) 