import logging

class GatingNode:
    """Evaluates drift and determines if a fork is necessary."""

    def __init__(self, config: dict = None):
        self.logger = logging.getLogger("Core.GatingNode")
        self.config = config or {}
        # Default max_depth, can be overridden via config
        self.max_depth = self.config.get('max_breath_cycle_depth', 10)
        self.logger.info(f"GatingNode initialized. Max depth for threshold calc: {self.max_depth}")

    def evaluate_drift(self, drift_vector, cycle_depth: int = 1) -> bool:
        """Evaluate drift based on the vector and current cycle depth.

        Args:
            drift_vector: A numerical representation of the current drift.
                          (Placeholder: assumes a single float value for now).
            cycle_depth: The current depth in the breath cycle recursion.

        Returns:
            True if drift exceeds threshold (fork needed), False otherwise.
        """
        if drift_vector is None:
            self.logger.warning("evaluate_drift called with None drift_vector. Assuming no fork needed.")
            return False

        # --- Accepted Dynamic Threshold Formula ---
        # Ensure cycle_depth doesn't cause division by zero or negative thresholds
        clamped_depth = max(1, cycle_depth)
        normalized_depth = min(1.0, clamped_depth / self.max_depth) # Normalize depth between 0 and 1
        threshold = 0.1 + (0.2 * normalized_depth)
        # ----------------------------------------

        # Placeholder: Assume drift_vector is a single float magnitude for now
        # TODO: Implement more sophisticated drift vector analysis
        current_drift_magnitude = float(drift_vector) if isinstance(drift_vector, (int, float)) else 0.0

        should_fork = current_drift_magnitude > threshold

        self.logger.debug(
            f"Evaluating drift: Magnitude={current_drift_magnitude:.4f}, "
            f"CycleDepth={cycle_depth}, Threshold={threshold:.4f} -> Fork Needed: {should_fork}"
        )
        return should_fork

# --- Add __init__.py if it doesn't exist ---
# (Ensure vanta_seed/core is a package)
# Create an empty vanta_seed/core/__init__.py if needed. 