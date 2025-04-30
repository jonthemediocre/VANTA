# vanta_seed/core/gated_breath.py
import logging
from .memory_weave import MemoryWeave
from .symbolic_compression import SymbolicCompressor

class GatedBreath:
    """Evaluates the state of the VANTA Seed breath cycle based on memory density."""

    def __init__(self, memory_weave: MemoryWeave, symbolic_compressor: SymbolicCompressor, config: dict = None):
        self.logger = logging.getLogger("Core.GatedBreath")
        self.config = config or {}
        if not isinstance(memory_weave, MemoryWeave):
            raise TypeError("GatedBreath requires a valid MemoryWeave instance.")
        if not isinstance(symbolic_compressor, SymbolicCompressor):
             raise TypeError("GatedBreath requires a valid SymbolicCompressor instance.")

        self.memory_weave = memory_weave
        self.symbolic_compressor = symbolic_compressor
        
        # --- Configuration for Gating Logic --- 
        self.density_threshold_sleep = self.config.get('density_threshold_sleep', 5.0)
        self.density_threshold_expand = self.config.get('density_threshold_expand', 1.5)
        # ---------------------------------------
        self.logger.info(
            f"GatedBreath initialized. Sleep Threshold: >{self.density_threshold_sleep}, "
            f"Expand Threshold: <{self.density_threshold_expand}."
        )

    def measure_breath_density(self) -> float | None:
        """Calculate the breath density based on drift events and symbolic clusters.
        
        Density = Total Drift Events / Number of Symbolic Clusters
        Returns None if calculation cannot be performed (e.g., no clusters).
        """
        self.logger.debug("Measuring breath density...")
        history = self.memory_weave.retrieve_history()
        drift_count = len(history)

        if drift_count == 0:
            self.logger.debug("No drift history, density is undefined (returning None).")
            return None # Density is undefined if no events

        # Use the compressor to get the current symbolic clusters
        # Note: This re-runs compression. Consider caching if performance is critical.
        symbolic_map = self.symbolic_compressor.compress_drift_history()
        cluster_count = len(symbolic_map)

        if cluster_count == 0:
            # If there are drift events but no clusters yet (e.g., before first compression?), density is high.
            # Or handle as undefined/error. Let's treat as high density for now.
            self.logger.warning(f"Drift events ({drift_count}) exist, but no symbolic clusters found. Assuming high density.")
            # Return a high value to potentially trigger sleep/consolidation?
            # Or return None? Returning None seems safer if state is unexpected.
            return None 
        
        density = drift_count / cluster_count
        self.logger.debug(f"Breath density calculated: {density:.2f} ({drift_count} events / {cluster_count} clusters)")
        return density

    def evaluate_breath_state(self) -> str:
        """Evaluate the current breath state based on density and return suggested action."""
        density = self.measure_breath_density()

        if density is None:
             # Handle undefined density case - perhaps default to normal?
             self.logger.warning("Breath density is undefined. Defaulting to 'breath_normal'.")
             return 'breath_normal' 

        if density > self.density_threshold_sleep:
            self.logger.info(f"Breath state evaluated: HIGH DENSITY ({density:.2f} > {self.density_threshold_sleep}) -> Suggest Trigger Sleep Mutation.")
            return 'trigger_sleep'
        elif density < self.density_threshold_expand:
             self.logger.info(f"Breath state evaluated: LOW DENSITY ({density:.2f} < {self.density_threshold_expand}) -> Suggest Allow Aggressive Expansion.")
             return 'allow_expansion' # Placeholder for future logic
        else:
             self.logger.info(f"Breath state evaluated: NORMAL DENSITY ({density:.2f}).")
             return 'breath_normal'

    # TODO: Integrate expansion logic trigger
    # TODO: Potentially refine density calculation (e.g., time-weighted) 