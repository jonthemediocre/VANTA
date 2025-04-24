# VANTA Best Practices

## 1. Conversation
* Always mirror user tone; do not soften unless asked.
* Prepend `[(SceneTrigger::START)]` for ritual initiation.
* Use `<think>` block for internal reasoning; close before final answer.

## 2. Memory Management
* Route all persistent data to /FrAmEwOrK/memory/persistent.
* Ephemeral reflections go to /memory/events as timestamped JSONL.

## 3. Model Routing
* Use `TaskRouter.pick_model()` logic; allow override via user flag `model:`.
* For vision input, always pass through Llama‑4 first, even if ultimately text answered.

## 4. Art Generation
* Follow Style Guide; keep aspect ratio square for book pages.
* Use variable seeds to avoid mode collapse; sample 4 drafts then vote (Best‑of‑N).

## 5. Fine‑tuning vs LoRA
* Default to LoRA (rank ≤ 64) unless ROI > $100 k/yr.
* Store adapters in /lora_templates; load lazily on router startup.