from enum import Enum
from typing import Any, Dict, Optional, List # Added List

# --- Forward reference for MemoryWeave --- 
# Attempting to import directly might cause circular dependencies later
# Instead, we'll use the reference passed in __init__
# from vanta_seed.core.memory_weave import MemoryWeave 
# -----------------------------------------

class TrinityRole(Enum):
# ... existing code ...
    def __init__(self, global_memory_weave_ref: Optional[Any] = None):
        """Initialize Trinity Node Memory.
        
        Args:
            global_memory_weave_ref: Optional reference to the main MemoryWeave instance.
        """
        self.echoes: Dict[str, Any] = {} # Local short-term memory / state
        self.destiny_constraints: Dict[str, Any] = {} # Constraints passed down
        self.global_memory = global_memory_weave_ref # Store reference
        print(f"TrinityNodeMemory initialized. Global MemoryWeave available: {self.global_memory is not None}")

    def update_echo(self, key: str, value: Any):
        """Update local short-term memory."""
# ... existing code ...
    def get_constraint(self, key: str) -> Optional[Any]:
        return self.destiny_constraints.get(key)
        
    # --- Methods to interact with Global MemoryWeave --- 
    def get_global_history(self, limit: int = 10) -> List[Dict]:
        """Retrieve recent snapshots from the global MemoryWeave."""
        if self.global_memory and hasattr(self.global_memory, 'retrieve_history'):
            try:
                 return self.global_memory.retrieve_history(limit=limit)
            except Exception as e:
                 print(f"Error retrieving global history from MemoryWeave: {e}")
                 return []
        print("Warning: Global MemoryWeave reference not available in TrinityNodeMemory.")
        return []
        
    def lookup_global_memory(self, query: str, search_limit: int = 20) -> List[Dict]:
        """Perform a lookup in the global MemoryWeave."""
        if self.global_memory and hasattr(self.global_memory, 'lookup_memory'):
             try:
                  return self.global_memory.lookup_memory(query=query, search_limit=search_limit)
             except Exception as e:
                  print(f"Error looking up global memory in MemoryWeave: {e}")
                  return []
        print("Warning: Global MemoryWeave reference not available for lookup.")
        return []
        
    def get_global_archetype_metadata(self, token: str) -> Optional[Dict]:
        """Get metadata for a specific archetype from global MemoryWeave."""
        if self.global_memory and hasattr(self.global_memory, 'get_archetype_metadata'):
            try:
                 return self.global_memory.get_archetype_metadata(token)
            except Exception as e:
                 print(f"Error getting archetype metadata from MemoryWeave: {e}")
                 return None
        print("Warning: Global MemoryWeave reference not available for archetype metadata.")
        return None
    # --- Potential TODO: push_local_echo_to_global --- 
    # (Depends if local state needs explicit pushing or if Executors handle it)
    # --------------------------------------------------- 