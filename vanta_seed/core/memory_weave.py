import logging
import json
from datetime import datetime
from typing import List, Dict

class MemoryWeave:
    """Anchors archetype tokens and branch drift summaries."""

    def __init__(self, config: dict = None):
        self.logger = logging.getLogger("Core.MemoryWeave")
        self.config = config or {}
        # Simple in-memory stores for now
        # Registry maps archetype_token -> {metadata, creation_timestamp}
        self.archetype_registry: dict[str, dict] = {}
        # List of drift snapshots, each a dict
        self.drift_snapshots: list[dict] = []
        self.logger.info("MemoryWeave initialized.")

    def register_archetype(self, token: str, metadata: dict):
        """Register a new archetype token with its associated metadata."""
        if token in self.archetype_registry:
            self.logger.warning(f"Archetype token '{token}' already registered. Overwriting metadata.")
        timestamp = datetime.utcnow().isoformat()
        self.archetype_registry[token] = {
            "metadata": metadata,
            "registered_at": timestamp
        }
        self.logger.info(f"Registered archetype: {token}")

    def snapshot_drift(self, branch_state: dict):
        """Record a snapshot of the current branch state, including drift info."""
        if 'archetype_token' not in branch_state:
             self.logger.error("Attempted to snapshot drift without 'archetype_token'. Skipping.")
             # Consider adding a default/unknown token or raising an error based on strictness needs
             return

        timestamp = datetime.utcnow().isoformat()
        snapshot = {
            "timestamp": timestamp,
            **branch_state # Unpack the provided state into the snapshot
        }
        self.drift_snapshots.append(snapshot)
        self.logger.debug(f"Drift snapshot taken for archetype {branch_state['archetype_token']}")

    def retrieve_history(self, limit: int = None) -> list[dict]:
        """Retrieve the recorded drift snapshots, optionally limited to the most recent."""
        if limit and limit > 0:
            return self.drift_snapshots[-limit:]
        return self.drift_snapshots

    def get_archetype_metadata(self, token: str) -> dict | None:
         """Retrieve metadata for a specific archetype token."""
         return self.archetype_registry.get(token)

    # --- [Suggest Minor Mutation] --- Optional Visualization Method ---
    def visualize_drift_history_ascii(self, limit: int = 20) -> str:
        """Generate a simple ASCII representation of the recent drift history."""
        history = self.retrieve_history(limit=limit)
        if not history:
            return "No drift history recorded."

        # Corrected multi-line string initialization
        output = "Drift History (Recent First):\n"
        output += "-----------------------------\n"

        # Simple linear list for now, could be enhanced with tree structure later
        for snapshot in reversed(history):
            token = snapshot.get('archetype_token', '[No Token]')
            ts = snapshot.get('timestamp', '')
            drift = snapshot.get('drift_vector', 'N/A') # Assuming drift_vector exists
            decision = snapshot.get('decision', 'N/A') # Assuming decision exists
            reason = snapshot.get('reason', '')

            # Basic formatting, assuming drift_vector is simple for now
            drift_str = f"{drift:.4f}" if isinstance(drift, (int, float)) else str(drift)

            output += f"[{ts}] {token} | Decision: {decision} | Drift: {drift_str}\n"
            if reason:
                output += f"  Reason: {reason}\n"

        output += "-----------------------------"
        return output

    def visualize_drift_history_mermaid(self, limit: int = 20) -> str:
        """Generate a Mermaid graphviz representation of the drift history (experimental)."""
        history = self.retrieve_history(limit=limit)
        if not history:
            return "graph TD\nA[No History];"

        output = "graph TD\n"
        nodes = {}
        edges = []
        root_node = None

        for i, snapshot in enumerate(history):
            token = snapshot.get('archetype_token', f'Snapshot_{i}')
            # Sanitize ID more robustly
            safe_token = "".join(c if c.isalnum() or c in '_' else '_' for c in token)[:20]
            node_id = f"N{i}_{safe_token}"

            nodes[node_id] = snapshot # Store snapshot info with the node ID

            # Basic labeling - can be enhanced
            drift = snapshot.get('drift_vector', 'N/A')
            drift_str = f"{drift:.2f}" if isinstance(drift, (int, float)) else str(drift)
            # Ensure label string is properly quoted for Mermaid
            label_content = f'{token}<br>Drift: {drift_str}'
            label = f'{node_id}["{label_content}"]'
            output += f"    {label}\n"

            # --- Experimental Edge Logic --- 
            # Try to link based on source branches if it's a merge, or find the previous snapshot
            decision = snapshot.get('decision')
            parent_node_id = None

            if decision == 'merge_branches':
                 # TODO: Need a way to map source branch IDs back to previous snapshot node IDs
                 # This requires more sophisticated state tracking than currently available
                 pass # Skip merge edges for now
            elif i > 0:
                 # Simple linear link to previous snapshot for now
                 prev_snapshot = history[i-1]
                 prev_token = prev_snapshot.get('archetype_token', f'Snapshot_{i-1}')
                 # Re-apply robust sanitization
                 safe_prev_token = "".join(c if c.isalnum() or c in '_' else '_' for c in prev_token)[:20]
                 parent_node_id = f"N{i-1}_{safe_prev_token}"

            if parent_node_id and parent_node_id in nodes:
                 edges.append(f"    {parent_node_id} --> {node_id}")
            elif root_node is None:
                 root_node = node_id # First node becomes root if no parent found

        # Add edges to output
        output += "\n".join(edges)

        # Style nodes (optional)
        # output += "\n    style N0 fill:#f9f"

        return output
    # --- End Optional Visualization ---

    def lookup_memory(self, query: str, search_limit: int = 50) -> List[Dict]:
        """Searches recent memory snapshots for a given query string.

        Args:
            query: The string to search for (case-insensitive).
            search_limit: The maximum number of recent snapshots to search.

        Returns:
            A list of matching snapshot dictionaries.
        """
        self.logger.debug(f"Performing memory lookup for query: '{query}'")
        query_lower = query.lower()
        matches = []
        # Search the most recent snapshots first
        search_space = self.retrieve_history(limit=search_limit)

        for snapshot in reversed(search_space): # Iterate recent -> older
            match_found = False
            # Check reason field
            reason = snapshot.get('reason', '')
            if isinstance(reason, str) and query_lower in reason.lower():
                match_found = True
            
            # Check archetype token
            token = snapshot.get('archetype_token', '')
            if isinstance(token, str) and query_lower in token.lower():
                 match_found = True
                 
            # Check payload (simple string search in values for now)
            payload = snapshot.get('payload', {})
            if isinstance(payload, dict):
                for value in payload.values():
                    if isinstance(value, str) and query_lower in value.lower():
                         match_found = True
                         break # Found in payload
            
            if match_found:
                matches.append(snapshot)
                self.logger.debug(f"Match found for '{query}' in snapshot for token {token}")

        self.logger.info(f"Memory lookup for '{query}' found {len(matches)} match(es) in last {search_limit} snapshots.")
        return matches # Return newest matches first

# --- Add __init__.py if it doesn't exist ---
# (Ensure vanta_seed/core is a package)
# Create an empty vanta_seed/core/__init__.py if needed. 