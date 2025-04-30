# vanta_seed/core/vitals_layer.py
import logging
import statistics # For calculating average
from .memory_weave import MemoryWeave
from .identity_trees import IdentityTrees

class VitalsLayer:
    """Monitors the health, drift stability, and symbolic integrity of VANTA Seed."""

    def __init__(self, memory_weave: MemoryWeave, identity_trees: IdentityTrees, config: dict = None):
        self.logger = logging.getLogger("Core.VitalsLayer")
        self.config = config or {}
        if not isinstance(memory_weave, MemoryWeave):
            raise TypeError("VitalsLayer requires a valid MemoryWeave instance.")
        if not isinstance(identity_trees, IdentityTrees):
             raise TypeError("VitalsLayer requires a valid IdentityTrees instance.")

        self.memory_weave = memory_weave
        self.identity_trees = identity_trees
        
        # Initialize vitals dictionary
        self.vitals = {
            "assessment_timestamp": None,
            "total_drift_events": 0,
            "average_drift_magnitude": 0.0,
            "max_drift_magnitude": 0.0,
            "drift_std_dev": 0.0,
            "total_archetypes_registered": 0,
            "identity_roots_count": 0,
            "identity_branches_count": 0,
            "broken_lineages_detected": 0,
            "symbolic_collapse_health": 1.0  # Placeholder
        }
        self.logger.info("VitalsLayer initialized.")

    def assess_health(self) -> dict:
        """Scan current memory and identity structures to update vitals.
        
        Returns:
            The updated vitals dictionary.
        """
        self.logger.debug("Assessing VANTA Seed health vitals...")
        current_vitals = self.vitals # Work on the instance dict
        current_vitals["assessment_timestamp"] = datetime.utcnow().isoformat()

        # --- Memory Weave Vitals --- 
        history = self.memory_weave.retrieve_history()
        drift_count = len(history)
        current_vitals["total_drift_events"] = drift_count
        current_vitals["total_archetypes_registered"] = len(self.memory_weave.archetype_registry)

        if drift_count > 0:
            # Calculate drift statistics
            drift_magnitudes = []
            for snapshot in history:
                 drift = snapshot.get('drift_vector', 0.0)
                 # Ensure drift is numeric
                 if isinstance(drift, (int, float)):
                     drift_magnitudes.append(abs(drift)) 
                 else:
                     # Log problematic drift value, but don't break calculation
                     self.logger.warning(f"Non-numeric drift value encountered: {drift} in snapshot for token {snapshot.get('archetype_token')}")
                     drift_magnitudes.append(0.0) # Treat non-numeric as zero drift for stats
            
            if drift_magnitudes:
                current_vitals["average_drift_magnitude"] = statistics.mean(drift_magnitudes)
                current_vitals["max_drift_magnitude"] = max(drift_magnitudes)
                if len(drift_magnitudes) > 1:
                    current_vitals["drift_std_dev"] = statistics.stdev(drift_magnitudes)
                else:
                    current_vitals["drift_std_dev"] = 0.0
            else:
                 # Case where drift_vector existed but wasn't numeric
                 current_vitals["average_drift_magnitude"] = 0.0
                 current_vitals["max_drift_magnitude"] = 0.0
                 current_vitals["drift_std_dev"] = 0.0
        else:
            # No history, reset drift stats
            current_vitals["average_drift_magnitude"] = 0.0
            current_vitals["max_drift_magnitude"] = 0.0
            current_vitals["drift_std_dev"] = 0.0
        # --------------------------

        # --- Identity Tree Vitals --- 
        current_vitals["identity_roots_count"] = len(self.identity_trees.identity_roots)
        current_vitals["identity_branches_count"] = len(self.identity_trees.lineage_map)
        # Check lineage integrity (Simplified check: look for orphans in lineage map)
        broken = 0
        all_known_tokens = set(self.identity_trees.identity_roots.keys()) | set(self.identity_trees.lineage_map.keys())
        for child, parent in self.identity_trees.lineage_map.items():
            if parent not in all_known_tokens:
                self.logger.warning(f"Broken lineage detected: Parent '{parent}' for child '{child}' not found in roots or other branches.")
                broken += 1
        current_vitals["broken_lineages_detected"] = broken
        # ---------------------------

        # --- Symbolic Collapse Health (Placeholder) --- 
        # TODO: Implement logic based on SymbolicCompressor output or other metrics
        current_vitals["symbolic_collapse_health"] = 1.0 # Placeholder
        # --------------------------------------------

        self.logger.info("Vitals assessment complete.")
        # Log key vitals
        self.logger.info(f"Vitals Summary: Events={drift_count}, AvgDrift={current_vitals['average_drift_magnitude']:.4f}, Roots={current_vitals['identity_roots_count']}, Branches={current_vitals['identity_branches_count']}")
        return current_vitals

    def visualize_vitals(self) -> str:
        """Return a simple text dashboard of the most recently assessed vitals."""
        if self.vitals.get("assessment_timestamp") is None:
            return "Vitals assessment has not run yet."
        
        output = f"VANTA Seed Vitals (Assessed: {self.vitals['assessment_timestamp']})\n"
        output += "--------------------------------------------------\n"
        # Format vitals nicely
        output += f"- Total Drift Events:          {self.vitals['total_drift_events']}\n"
        output += f"- Total Archetypes Registered: {self.vitals['total_archetypes_registered']}\n"
        output += f"- Avg Drift Magnitude:         {self.vitals['average_drift_magnitude']:.4f}\n"
        output += f"- Max Drift Magnitude:         {self.vitals['max_drift_magnitude']:.4f}\n"
        output += f"- Drift Std Dev:             {self.vitals['drift_std_dev']:.4f}\n"
        output += f"- Identity Roots:            {self.vitals['identity_roots_count']}\n"
        output += f"- Identity Branches:         {self.vitals['identity_branches_count']}\n"
        output += f"- Broken Lineages Detected:  {self.vitals['broken_lineages_detected']}\n"
        output += f"- Symbolic Collapse Health:  {self.vitals['symbolic_collapse_health']:.2f} (Placeholder)\n"
        output += "--------------------------------------------------"
        return output

# Need datetime for timestamping assessments
from datetime import datetime 