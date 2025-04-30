# vanta_seed/core/sleep_mutator.py
import logging
import random
import copy
import uuid
from .memory_weave import MemoryWeave
from .symbolic_compression import SymbolicCompressor
from collections import defaultdict

class SleepMutator:
    """Applies passive, non-deterministic mutations to the drift history during sleep cycles.

    This simulates subconscious processing or random evolutionary changes.
    Mutations should be subtle and non-destructive (e.g., adding new drift points
    that are slight variations of existing ones).
    """
    def __init__(self, memory_weave: MemoryWeave, symbolic_compressor: SymbolicCompressor, config: dict = None):
        self.logger = logging.getLogger("Core.SleepMutator")
        self.memory_weave = memory_weave
        self.symbolic_compressor = symbolic_compressor # May be needed later for context
        self.config = config or {}
        # Configurable parameters for mutation
        self.mutation_probability = self.config.get('mutation_probability', 0.1) # Chance to mutate any given snapshot
        self.drift_perturbation_scale = self.config.get('drift_perturbation_scale', 0.05) # Max % change to drift vector
        self.logger.info("SleepMutator initialized.")

    # --- UPDATED Signature and Logic --- 
    def mutate_drift_passively(self, agent_age_map: dict[str, int] = None, limit: int = 100) -> int:
        """Applies small random drift mutations to memory snapshots during sleep.
        Mutations are non-destructive (appends new variations) and biased towards
        snapshots from younger agents.
        
        Args:
            agent_age_map: Optional map of {agent_id: age} to bias mutations.
                           If None, mutations are uniformly random.
            limit: The maximum number of mutations to apply in this cycle.
        
        Returns:
            The total number of successful mutations applied.
        """
        self.logger.info(f"Initiating passive drift mutation cycle (Limit: {limit}).")
        
        # 1. Retrieve candidate snapshots from MemoryWeave
        # Consider retrieving only recent history or based on other criteria?
        all_snapshots = self.memory_weave.retrieve_history()
        if not all_snapshots:
            self.logger.info("No drift history found. Skipping sleep mutation.")
            return 0
            
        # 2. Filter snapshots with a source agent (needed for weighting)
        candidate_snapshots = [s for s in all_snapshots if s.get('source_agent')]
        if not candidate_snapshots:
             self.logger.info("No snapshots with source_agent found. Skipping weighted mutation.")
             # Optionally, could still apply uniform random mutation here
             return 0
             
        # 3. Compute Weights based on Agent Age
        weights = []
        snapshot_indices = list(range(len(candidate_snapshots)))
        
        for i in snapshot_indices:
            snapshot = candidate_snapshots[i]
            agent_id = snapshot.get('source_agent')
            weight = 1.0 # Default weight
            if agent_age_map is not None and agent_id:
                age = agent_age_map.get(agent_id, 0) # Default age 0 if not in map
                # Weight decreases with age: age 0 -> 1.0, age 1 -> 0.5, age 2 -> 0.33 etc.
                # Add small epsilon to avoid division by zero if age is -1? (Shouldn't happen)
                weight = 1.0 / (1.0 + max(0, age)) 
            weights.append(weight)
            
        # Normalize weights (optional but good practice if sum is not 1)
        total_weight = sum(weights)
        if total_weight == 0:
             self.logger.warning("Total weight for mutation candidates is zero. Skipping mutation.")
             return 0
             
        normalized_weights = [w / total_weight for w in weights]

        # 4. Select Snapshots to Mutate (Weighted Random Sampling)
        # Using random.choices which supports weights (available in Python 3.6+)
        try:
            indices_to_mutate = random.choices(
                 snapshot_indices,
                 weights=normalized_weights, 
                 k=min(limit, len(candidate_snapshots)) # Select up to limit or total candidates
            )
        except ValueError as e:
             # Handle potential issue if weights don't sum to 1 or are negative (shouldn't happen here)
             self.logger.error(f"Error during weighted random sampling: {e}. Falling back to uniform sampling.")
             indices_to_mutate = random.sample(snapshot_indices, k=min(limit, len(candidate_snapshots)))
             
        snapshots_to_mutate = [candidate_snapshots[i] for i in indices_to_mutate]
        self.logger.info(f"Selected {len(snapshots_to_mutate)} snapshots for potential mutation (biased towards younger agents).")

        # 5. Apply Non-Destructive Mutations
        mutations_applied = 0
        mutation_counts_by_agent = defaultdict(int)
        
        for original_snapshot in snapshots_to_mutate:
            try:
                # --- Create a mutated copy --- 
                mutated_snapshot = copy.deepcopy(original_snapshot)
                
                # --- Modify Drift Vector (Example) --- 
                if 'drift_vector' in mutated_snapshot and isinstance(mutated_snapshot['drift_vector'], (int, float)):
                    perturbation = random.uniform(-self.drift_perturbation_scale, self.drift_perturbation_scale)
                    original_drift = mutated_snapshot['drift_vector']
                    mutated_snapshot['drift_vector' ] *= (1 + perturbation)
                    self.logger.debug(f"Mutating drift: {original_drift:.4f} -> {mutated_snapshot['drift_vector']:.4f}")
                else:
                     self.logger.debug(f"Skipping drift vector mutation for snapshot (missing or invalid type).")
                     
                # --- Update other fields --- 
                original_token = mutated_snapshot.get('archetype_token', 'UNKNOWN_ORIGINAL')
                new_token = f"DREAM::Mutated::{original_token}::{uuid.uuid4().hex[:6]}"
                mutated_snapshot['archetype_token'] = new_token
                mutated_snapshot['decision'] = 'sleep_mutation'
                mutated_snapshot['reason'] = f"Passive mutation during sleep from {original_token}"
                mutated_snapshot['parent_archetype_token'] = original_token # Link back to original
                mutated_snapshot['timestamp'] = self.memory_weave._get_timestamp() # Add new timestamp
                
                # --- Register new archetype --- 
                self.memory_weave.register_archetype(new_token, mutated_snapshot)
                
                # --- Append mutated snapshot to MemoryWeave history --- 
                self.memory_weave.snapshot_drift(mutated_snapshot)
                
                mutations_applied += 1
                agent_id = original_snapshot.get('source_agent', 'UnknownAgent')
                mutation_counts_by_agent[agent_id] += 1
                
                self.logger.debug(f"Applied sleep mutation: {original_token} -> {new_token}")

            except Exception as e:
                self.logger.error(f"Error applying mutation to snapshot derived from {original_snapshot.get('archetype_token')}: {e}", exc_info=True)
        
        # 6. Log Results
        self.logger.info(f"Sleep mutation cycle complete. Applied {mutations_applied} mutations (Limit: {limit}).")
        if mutations_applied > 0:
            self.logger.info("Mutations per agent:")
            for agent, count in mutation_counts_by_agent.items():
                 self.logger.info(f"  - {agent}: {count}")
                 
        return mutations_applied
    # ----------------------------------

    # TODO: Implement more sophisticated mutation strategies:
    # - Biased drift based on archetype clusters from SymbolicCompressor.
    # - Mutation based on snapshot age or relevance.
    # - Perturbing metadata fields instead of just drift_vector.

# Need datetime for timestamping mutations
from datetime import datetime 