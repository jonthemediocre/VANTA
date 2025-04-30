# vanta_seed/core/identity_trees.py
import logging
import uuid
from collections import defaultdict
from .memory_weave import MemoryWeave

class IdentityTrees:
    """Manages the lineage and identity relationships between memory archetypes.

    Tracks how different states (represented by archetype tokens) evolve from
    one another, forming potentially branching trees of identity.
    """

    def __init__(self, memory_weave: MemoryWeave, config: dict = None):
        self.logger = logging.getLogger("Core.IdentityTrees")
        self.memory_weave = memory_weave
        self.config = config or {}
        
        # Stores the root archetypes (tokens that started a lineage)
        # Value could be timestamp or initial metadata
        self.identity_roots: dict[str, dict] = {}
        
        # Stores the parent-child relationships: child_token -> parent_token
        self.lineage_map: dict[str, list[str]] = defaultdict(list)
        
        # Optional: Store additional context per token if needed beyond MemoryWeave
        # self.token_context: dict[str, dict] = {}

        self.logger.info("IdentityTrees initialized.")

    def root_identity(self, archetype_token: str):
        """Establishes a new root identity based on an archetype token."""
        if archetype_token in self.identity_roots or any(archetype_token in children for children in self.lineage_map.values()):
            self.logger.warning(f"Attempted to root an already existing or branched token: {archetype_token}. Ignoring.")
            return
        
        # Retrieve metadata to store with the root (optional)
        metadata = self.memory_weave.get_archetype_metadata(archetype_token)
        self.identity_roots[archetype_token] = metadata or {"created_at": uuid.uuid4().hex[:8]} # Basic metadata if none found
        self.logger.info(f"Established new identity root: {archetype_token}")

    def branch_identity(self, parent_token: str, child_token: str):
        """Creates a branch from a parent token to a child token."""
        if child_token in self.lineage_map or child_token in self.identity_roots:
            self.logger.error(f"Attempted to branch TO an already existing token: {child_token}. This might indicate a logic error.")
            # Decide on handling: overwrite, ignore, raise? For now, log error and ignore.
            return
            
        if parent_token not in self.identity_roots and not any(parent_token in children for children in self.lineage_map.values()):
            self.logger.warning(f"Attempted to branch from non-existent parent token: {parent_token}. Auto-rooting parent.")
            self.root_identity(parent_token)
            if parent_token not in self.identity_roots:
                 self.logger.error(f"Failed to auto-root parent {parent_token}. Cannot branch {child_token}.")
                 return
        if parent_token == child_token:
            self.logger.error(f"Cannot branch a token to itself: {parent_token}")
            return
        if child_token in self.lineage_map.get(parent_token, []):
             self.logger.debug(f"Branch from {parent_token} to {child_token} already exists. Ignoring duplicate.")
             return

        self.lineage_map[parent_token].append(child_token)
        self.logger.info(f"Branched identity: {parent_token} --> {child_token}")
        
        # If the child was previously a root, remove it from roots as it now has a parent
        if child_token in self.identity_roots:
            self.logger.debug(f"Child token {child_token} was previously a root. Removing from roots list.")
            del self.identity_roots[child_token]

    def retrieve_lineage(self, archetype_token: str) -> list[str]:
        """Retrieves the full lineage (ancestors) leading to a specific token."""
        lineage = [archetype_token]
        current_token = archetype_token
        processed = set() # Prevent infinite loops
        while current_token not in processed:
            processed.add(current_token)
            parent_found = False
            for parent, children in self.lineage_map.items():
                if current_token in children:
                    if parent in processed:
                        self.logger.warning(f"Cycle detected in lineage retrieval for {archetype_token} at parent {parent}. Stopping trace.")
                        parent_found = False # Treat as end of trace
                        break
                    lineage.insert(0, parent)
                    current_token = parent
                    parent_found = True
                    break
            if not parent_found:
                break 
        return lineage

    def get_children(self, archetype_token: str) -> list[str]:
         """Gets the direct children of a given archetype token."""
         return self.lineage_map.get(archetype_token, [])

    def visualize_trees_ascii(self) -> str:
         """Generates a simple ASCII representation of all identity trees."""
         lines = ["Identity Trees (ASCII):"]
         processed_nodes = set()

         def _build_tree_lines(token, indent_level):
             prefix = "  " * indent_level
             lines.append(f"{prefix}🌳 {token}")
             processed_nodes.add(token)
             children = self.lineage_map.get(token, [])
             for i, child in enumerate(children):
                  if child not in processed_nodes: # Prevent cycles in visualization
                      _build_tree_lines(child, indent_level + 1)
                  else:
                       lines.append(f"{'  ' * (indent_level + 1)}🔄 {child} (Cycle Detected)")

         # Start from each root
         root_keys = list(self.identity_roots.keys()) # Get keys safely
         for root_token in root_keys:
             if root_token not in processed_nodes:
                  _build_tree_lines(root_token, 0)
                  
         # Check for orphans (nodes in lineage map but not reachable from roots)
         all_children = set(c for children in self.lineage_map.values() for c in children)
         all_parents = set(self.lineage_map.keys())
         potential_orphans = (all_parents | all_children) - processed_nodes - set(root_keys)
         if potential_orphans:
             lines.append("\nOrphaned Nodes/Cycles:")
             for orphan in potential_orphans:
                  if orphan not in processed_nodes: # Only print orphans not already shown in cycles
                      # Try to show their subtree if they are parents in the map
                      _build_tree_lines(orphan, 0) 

         return "\n".join(lines)
         
    # --- NEW: ASCII Tree Generator (Refined) --- 
    def generate_ascii_tree(self, root_id=None, indent=0, processed=None) -> str:
        """Generates an ASCII tree representation starting from roots or a specific ID."""
        if processed is None:
            processed = set()
            
        lines = []
        if root_id is None:
            # Start from all current roots
            roots = list(self.identity_roots.keys())
        else:
            # Start from the specified root_id
            roots = [root_id] if root_id in self.identity_roots or any(root_id in v for v in self.lineage_map.values()) else []
            if not roots:
                 return f"(Node {root_id} not found as root or child)"
                 
        for root in roots:
            if root in processed: # Avoid infinite loops in case of cycles
                lines.append("  " * indent + f"🔄 {root} (Cycle/Repeat)")
                continue
            
            prefix = "| " * indent # More tree-like structure
            lines.append(prefix + f"+--🌳 {root}")
            processed.add(root)
            
            children = self.lineage_map.get(root, [])
            for i, child in enumerate(children):
                 # Generate subtree recursively
                 subtree_lines = self.generate_ascii_tree(child, indent + 1, processed).split('\n')
                 # Adjust prefix for child lines
                 for line in subtree_lines:
                      if line.strip(): # Avoid adding empty lines
                          lines.append("| " * indent + "|  " + line)
                          
        # Only return joined lines if this is the top-level call
        if indent == 0:
            # Add title and potentially orphan check here if desired
            final_lines = ["=== Swarm Tree (ASCII) ==="] + lines
            # Optional Orphan Check (can be slow)
            # all_nodes = set(self.identity_roots.keys()) | set(p for p in self.lineage_map) | set(c for children in self.lineage_map.values() for c in children)
            # orphans = all_nodes - processed
            # if orphans:
            #     final_lines.append("\n=== Orphaned Nodes ===")
            #     for orphan in orphans:
            #         final_lines.append(f"- {orphan}")
            return "\n".join(final_lines)
        else:
             return "\n".join(lines) # Return intermediate lines for recursion
    # ----------------------------------------

    # --- NEW: Mermaid Mindmap Generator --- 
    def generate_mermaid_mindmap(self) -> str:
        """Generates a Mermaid.js Mindmap definition string for the entire swarm lineage."""
        lines = [
            "graph TD",
            "    subgraph VANTA Swarm Lineage" # Fixed closing quote
        ]
        nodes_added = set()
        edges_added = set() # Prevent duplicate edges

        def add_node_and_children(node):
            if node not in nodes_added:
                # Sanitize node ID for Mermaid (Breakdown replace calls)
                safe_node_id = node.replace("::", "_")
                safe_node_id = safe_node_id.replace("-", "_")
                safe_node_id = safe_node_id.replace(" ", "_")
                lines.append(f"        {safe_node_id}["{node}"]") # Use safe ID for linking, display original
                nodes_added.add(node)
            
            # Sanitize parent ID separately
            safe_parent_id = node.replace("::", "_")
            safe_parent_id = safe_parent_id.replace("-", "_")
            safe_parent_id = safe_parent_id.replace(" ", "_")
            children = self.lineage_map.get(node, [])
            for child in children:
                 # Sanitize child ID separately
                 safe_child_id = child.replace("::", "_")
                 safe_child_id = safe_child_id.replace("-", "_")
                 safe_child_id = safe_child_id.replace(" ", "_")
                 edge = f"    {safe_parent_id} --> {safe_child_id}"
                 if edge not in edges_added:
                     lines.append(edge)
                     edges_added.add(edge)
                 add_node_and_children(child) # Recurse

        # Start traversal from all roots
        root_keys = list(self.identity_roots.keys())
        for root in root_keys:
            add_node_and_children(root)
            
        # Add orphaned subtrees (nodes that are parents but not children or roots)
        all_children_set = set(c for children in self.lineage_map.values() for c in children)
        orphan_parents = set(self.lineage_map.keys()) - all_children_set - set(root_keys)
        if orphan_parents:
            lines.append("    end") # End previous subgraph if needed
            lines.append("    subgraph Orphaned Trees")
            for orphan in orphan_parents:
                 if orphan not in nodes_added: # Check if already processed via a cycle perhaps
                      add_node_and_children(orphan)
            lines.append("    end")
        else:
             lines.append("    end") # End main subgraph

        return "\n".join(lines)
    # ------------------------------------

    # --- NEW: Agent Age Map Calculation --- 
    def compute_agent_age_map(self) -> dict[str, int]:
        """Computes agent age (depth) based on the identity tree structure.

        Returns:
            A dictionary mapping agent_id to its minimum depth (age) found in the trees.
        """
        agent_ages = {} # {agent_id: min_depth}
        processed_tokens = set() # To handle cycles during traversal

        def walk(token, depth):
            if token in processed_tokens:
                return # Already visited, break cycle
            processed_tokens.add(token)

            agent_id = self._extract_agent_id_from_token(token)
            if agent_id:
                # Update agent age only if the current path is shorter
                current_min_age = agent_ages.get(agent_id, float('inf'))
                if depth < current_min_age:
                    agent_ages[agent_id] = depth
                    self.logger.debug(f"Updated age for agent '{agent_id}' to {depth} via token {token}")
            
            # Recurse for children
            for child in self.lineage_map.get(token, []):
                walk(child, depth + 1)

        # Start walking from all roots
        root_keys = list(self.identity_roots.keys())
        for root_token in root_keys:
             walk(root_token, 0)
             
        self.logger.info(f"Computed agent age map for {len(agent_ages)} agents.")
        return agent_ages

    def _extract_agent_id_from_token(self, token: str) -> str | None:
        """Helper function to attempt extracting an agent ID from common token patterns."""
        parts = token.split("::")
        # Check common patterns where agent ID might be the 3rd element
        if len(parts) >= 3:
            # Patterns like ARCH::AGENT_INIT::<agent_id>::... 
            # or TASK::<task_type>::<agent_id>::... 
            # or ARCH::AGENT_SPAWN::<agent_id>::...
            potential_agent_id = parts[2]
            # Basic sanity check - could be more robust (e.g., check against known agents?)
            if potential_agent_id and not potential_agent_id.isdigit() and ' ' not in potential_agent_id:
                return potential_agent_id
        # Check pattern AGENT_STATE::<agent_id>::...
        elif len(parts) >= 2 and parts[0] == "AGENT_STATE":
             potential_agent_id = parts[1]
             if potential_agent_id and not potential_agent_id.isdigit() and ' ' not in potential_agent_id:
                return potential_agent_id
        
        # Add more pattern checks if needed based on actual token formats
        # self.logger.debug(f"Could not extract agent ID from token: {token}")
        return None
    # ------------------------------------

    # TODO: Add methods to query subtrees or find common ancestors. 