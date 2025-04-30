# VANTA-SEED Settings Reference

---

## ⚙️ Purpose: Configuring the Living Seed

This document provides a reference for the configurable parameters found in `vanta_seed/config/settings.yaml`.
These settings allow fine-tuning of VANTA-SEED's core behaviors, such as its breath cycle, memory reflection, and potentially future growth parameters.

If `settings.yaml` is missing or a specific key is absent, the system will use the default value specified here.

---

## 🔧 Core Behavior Settings

### `breaths_per_cycle`
- **Type:** `Integer`
- **Default:** `10`
- **Purpose:** Defines how many individual "breaths" (interactions or simulation steps, as tracked by `breath_tracker.py`) constitute a full breath cycle.
- **Impact:** This determines the frequency of potential Breath Expansion Rituals triggered via `breath_tracker.py` calling `breath_ritual_runner.py`.
- **Module:** `runtime/breath_tracker.py`

### `echo_reflex_interval`
- **Type:** `Integer`
- **Default:** `10`
- **Purpose:** Specifies the interval, in number of breaths, at which the **Breath Echo Reflex Ritual** is triggered.
- **Impact:** Controls how often VANTA-SEED automatically surfaces a random memory echo (`query_random_memory_echo`) during its operation. Setting to `0` or a negative value disables the reflex.
- **Module:** `runtime/breath_tracker.py`

### `memory_backend`
- **Type:** `String`
- **Default:** `"jsonl"`
- **Options:** `"jsonl"`, `"vector"` (Note: `"vector"` requires additional setup and dependencies not fully implemented)
- **Purpose:** Determines the storage mechanism used by `memory_engine.py`.
- **Impact:** 
    - `"jsonl"`: Uses simple, human-readable JSON Lines files in `vanta_seed/memory_storage/`. No external dependencies needed for core function.
    - `"vector"`: (Future) Would activate vector database storage (e.g., ChromaDB), enabling semantic search but requiring embedding models and database setup.
- **Module:** `memory/memory_engine.py` (Implementation needs to read this setting to switch logic)

---

## 🔮 Future Settings (Placeholder)

*(This section can be expanded as more configurable parameters are added)*

- **Mutation Settings:** (e.g., `base_mutation_chance`, `destiny_mutation_bias`)
- **Reasoning Parameters:** (e.g., `default_mythos_mode`, `logos_certainty_threshold`)
- **WhisperMode Configuration:** (e.g., `surrealism_level`, `dream_decay_factor`)

---

## 📝 Example `settings.yaml`

```yaml
# config/settings.yaml

# Adjust how many breaths complete a full cycle, triggering expansion checks
breaths_per_cycle: 15

# Make VANTA-SEED reflect on memories more often
echo_reflex_interval: 5

# --- Future example ---
# base_mutation_chance: 0.15 

# --- NEW SETTING --- 
# Specify the memory backend to use.
# Options: "jsonl" (simple file storage), "vector" (requires ChromaDB/embeddings - not fully implemented)
memory_backend: "jsonl"

```

--- 