from typing import List, Dict
import random
import uuid

class MutationEngine:
    # --- Candidate Generation & Operators ---
    def _generate_candidates(self, context: Dict, intensity: float, num_candidates: int) -> List[Dict]:
        """Generates mutation candidates by applying selected operators."""
        generated_candidates = []
        # Use context provided, which should include myths, config etc.
        operator_funcs = {
            "config_update": self._operator_config_update,
            "myth_addition": self._operator_myth_addition,
            "myth_perturbation": self._operator_myth_perturbation,
            # Add other operators here
        }
        available_ops = list(operator_funcs.keys())
        if not available_ops:
             logger.warning("No mutation operators available for candidate generation.")
             return []

        # Generate candidates by randomly selecting operators
        for _ in range(num_candidates * 2): # Generate more initially
             if not available_ops: break
             op_name = random.choice(available_ops)
             try:
                 results = operator_funcs[op_name](context, intensity) # Call the function
                 if results: # Operators return lists of candidate dicts
                     generated_candidates.extend(results)
             except Exception as e:
                  logger.error(f"Error executing operator '{op_name}': {e}", exc_info=True)


        # Limit number if needed
        if len(generated_candidates) > num_candidates:
             logger.debug(f"Generated {len(generated_candidates)} candidates, selecting {num_candidates} randomly.")
             actual_num_to_sample = min(num_candidates, len(generated_candidates))
             generated_candidates = random.sample(generated_candidates, actual_num_to_sample)

        logger.info(f"Generated {len(generated_candidates)} raw candidates using operators.")
        return generated_candidates

    # --- Example Operator Implementations (NOW WITH LOGIC from Patch v1.2) ---
    # --- Operator: config_update ---
    def _operator_config_update(self, context: Dict, intensity: float) -> List[Dict]:
        """Suggest a simple configuration change."""
        # TODO: Get actual configurable keys from core/config or blueprint
        config = context.get("config", {})
        configurable_keys = ["swarm_params.resonance_sensitivity", "agent_settings.SymbolicAgent.compression_level"]
        if not configurable_keys: return []

        target_key = random.choice(configurable_keys)
        # TODO: Need robust way to get/set nested keys from config dict
        current_value = config.get(target_key, 0.8) # Placeholder default - fetch real value
        if not isinstance(current_value, (int, float)):
            logger.warning(f"Config key '{target_key}' is not numeric, skipping config_update.")
            return []

        drift = (random.random() - 0.5) * intensity * 0.1 # Small drift
        new_value = round(max(0.1, min(1.0, current_value + drift)), 3) # Clamp between 0.1 and 1.0

        # Handle nested keys simply for now
        proposed_change_dict = {}
        keys = target_key.split('.')
        temp_dict = proposed_change_dict
        for i, key in enumerate(keys):
            if i == len(keys) - 1:
                temp_dict[key] = new_value
            else:
                temp_dict = temp_dict.setdefault(key, {})

        return [{
            "mutation_type": "config_update",
            "proposed_changes": proposed_change_dict,
            "description": f"Adjust config param '{target_key}' to {new_value}",
            "origin_agent": "MutationEngine",
            "requires_blessing": True,
            "mutation_operators_used": ["config_update"]
        }]

    # --- Operator: myth_addition ---
    def _operator_myth_addition(self, context: Dict, intensity: float) -> List[Dict]:
        """Suggest adding a new myth shard."""
        new_myth_id = f"myth-gen-{uuid.uuid4().hex[:6]}" # Need uuid import
        # TODO: Generate more meaningful content (LLM?)
        new_myth_content = f"At intensity {intensity:.2f}, a shard reflected {random.choice(['ancient light', 'future echoes', 'stillness', 'a forgotten bridge'])}."
        new_myth_name = f"Shard_{random.choice(['Light', 'Echo', 'Void', 'Bridge'])}_{new_myth_id[-4:]}"
        tags = [random.choice(["core", "agent", "ritual", "narrative"]), f"intensity_{int(intensity*10)}"]

        return [{
            "mutation_type": "myth_addition",
            "proposed_changes": { # Structure matches MythShard
                "id": new_myth_id,
                "name": new_myth_name,
                "content": new_myth_content,
                "tags": tags,
                "source": "mutated",
                "version": 1
            },
            "description": f"Propose new myth shard '{new_myth_name}' ({new_myth_id})",
            "origin_agent": "MutationEngine",
            "requires_blessing": True,
            "mutation_operators_used": ["myth_addition"]
        }]

    # --- Operator: myth_perturbation ---
    def _operator_myth_perturbation(self, context: Dict, intensity: float) -> List[Dict]:
        """Suggest small changes to existing active myths."""
        myths: List[MythShard] = context.get("myths", []) # Expect list of MythShard objects
        if not myths: return []

        selected_myth = random.choice(myths)
        # TODO: Implement sophisticated perturbation
        prefix = random.choice(["Consider that ", "Yet, it might be that ", "Perhaps instead, ", "The inverse suggests "])
        original_content = getattr(selected_myth, 'content', '')
        if not isinstance(original_content, str): original_content = str(original_content)
        current_version = getattr(selected_myth, 'version', 1) # Default to 1 if no version

        perturbed_content = prefix + original_content + f"\n(Ritual Perturbation v{current_version + 1} @ intensity {intensity:.2f})"

        return [{
            "mutation_type": "myth_update", # Distinct type for updates
            "target_element_id": selected_myth.id, # ID of the myth being changed
            "proposed_changes": { # Changes to apply to the myth
                "content": perturbed_content,
                "version": current_version + 1
            },
            "description": f"Perturb content of myth '{getattr(selected_myth, 'name', selected_myth.id)}' ({selected_myth.id})",
            "origin_agent": "MutationEngine",
            "requires_blessing": True,
            "source_element_ids": [selected_myth.id], # Lineage tracking
            "mutation_operators_used": ["myth_perturbation"]
        }]
    # --- Add other operators here ---


    # --- Candidate Evaluation & Selection ---
# ... existing code ... 