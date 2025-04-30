# vanta_seed/core/symbolic_compression.py
import logging
from .memory_weave import MemoryWeave

class SymbolicCompressor:
    """Handles archetypal compression of branch histories into condensed symbols."""

    def __init__(self, memory_weave: MemoryWeave, config: dict = None):
        self.logger = logging.getLogger("Core.SymbolicCompressor")
        self.config = config or {}
        if not isinstance(memory_weave, MemoryWeave):
            raise TypeError("SymbolicCompressor requires a valid MemoryWeave instance.")
        self.memory_weave = memory_weave
        self.logger.info("SymbolicCompressor initialized.")

    def compress_drift_history(self) -> dict:
        """Analyze drift snapshots, cluster related archetypes, and generate condensed symbols.

        Current basic strategy: Group archetype tokens by BranchType and Hint.
        Returns:
            A dictionary where keys are cluster identifiers (e.g., "FORK::Explore")
            and values are lists of archetype tokens belonging to that cluster.
        """
        self.logger.debug("Compressing drift history into symbolic clusters...")
        compressed_symbols = {}
        history = self.memory_weave.retrieve_history()
        archetype_registry = self.memory_weave.archetype_registry # Access registry directly for efficiency

        if not history:
            self.logger.info("No drift history found to compress.")
            return compressed_symbols

        processed_tokens = set() # Avoid processing the same token multiple times if snapshotted repeatedly

        for snapshot in history:
            # Use the archetype token directly from the snapshot
            token = snapshot.get("archetype_token")
            if not token or token in processed_tokens:
                continue

            # Retrieve metadata efficiently from the registry
            archetype_info = archetype_registry.get(token)
            if not archetype_info or 'metadata' not in archetype_info:
                self.logger.warning(f"Metadata not found for archetype token '{token}' in registry. Skipping.")
                continue

            metadata = archetype_info['metadata']
            # --- Basic Clustering Logic --- 
            # Extract branch type and hint if they exist in metadata
            # Handle cases where these keys might be missing
            branch_type = metadata.get('decision_type', 'UnknownType') # Corresponds to decision that created it
            # Hint might be less consistently available, fallback needed
            # Let's refine the cluster key based on available info
            hint = metadata.get('hint', 'NoHint') # Assuming hint might be added to metadata

            # Create a robust cluster key
            cluster_key = f"{branch_type}::{hint}" 
            # -----------------------------

            # Add token to the corresponding cluster
            if cluster_key not in compressed_symbols:
                compressed_symbols[cluster_key] = []
            compressed_symbols[cluster_key].append(token)
            processed_tokens.add(token) # Mark as processed

        self.logger.info(f"Compression complete. Found {len(compressed_symbols)} symbolic clusters.")
        # Log the generated clusters at debug level for inspection
        import json
        self.logger.debug(f"Compressed Symbol Map: {json.dumps(compressed_symbols, indent=2)}")

        return compressed_symbols

    # TODO: Add methods for more advanced clustering (e.g., using vector embeddings
    #       of archetype metadata or drift vectors).
    # TODO: Add methods to generate meta-symbols representing clusters. 