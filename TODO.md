# TODO List - Extracted from THEPLAN.md

- [DONE] DataUnifierAgent: Implement ML deduplication logic (Implemented basic sentence-transformer/cosine similarity; Implemented basic recency merge logic) in `vanta_seed/agents/data_unifier_agent.py`. (Scaffold/API/basic RL done; Registration done in `agents.index.mpc.json`).
- [High Priority] DataCatalogService: Scaffold `vanta_seed/services/data_catalog_service.py`, implement metadata store, schema registry, GraphQL/REST endpoints, and integrate with MemoryAgent.
- [High Priority] EntityResolutionAgent: Scaffold `vanta_seed/agents/entity_resolution_agent.py`, implement generative dedupe pipelines, hook into data ingestion, and surface metrics in dashboard.
- [High Priority] Containerization & Orchestration: Add Dockerfiles for each agent service, create Helm/OpenShift charts, and update CI/CD pipelines for seamless deployment.
- [Medium Priority] ComputeEstimatorAgent: Scaffold `vanta_seed/agents/compute_estimator_agent.py`, implement cost estimation formulas and endpoints, integrate with AutoMLService.
- [Medium Priority] LakehouseKnowledgeRepository: Scaffold `vanta_seed/services/lakehouse_repository.py`, implement Delta Lake/Iceberg integration, configure catalog and ACID transactions.
- [Medium Priority] AutoMLService: Scaffold `vanta_seed/services/automl_service.py`, integrate AutoGluon/TPOT for automated model discovery, and expose training job endpoints.
- [Medium Priority] ParallelSamplingAgent: Scaffold `vanta_seed/agents/parallel_sampling_agent.py`, implement parallel inference, ranking/ensemble logic, and sampling endpoints.
- [Medium Priority] MemoryGrafts: Scaffold `vanta_seed/memory/memory_graft.py`, implement graft ingestion, triggers, and RL-driven decay.
- [Medium Priority] SymbolicCompression: Scaffold `vanta_seed/agents/symbolic_compression.py`, implement symbolic compression and decompression pipelines.
- [Kernel - VantaSolve] Implement input validation/normalization in `VantaSolve.input_audit`.
- [Kernel - VantaSolve] Implement divergent thought generation (e.g., multi-temp LLM calls) in `VantaSolve.divergence`.
- [Kernel - VantaSolve] Implement consensus mechanism (e.g., voting, summarization) in `VantaSolve.consensus`.
- [Kernel - VantaSolve] Implement collapse/distillation mechanism (e.g., LLM summary) in `VantaSolve.collapse`.
- [Kernel - VantaSolve] Implement memory writing via orchestrator/memory engine in `VantaSolve.memory_binding`.
- [Kernel - VantaSolve] Replace `print` statements with proper logging using the `logging` module.
- [Kernel - VantaSolve] Add robust error handling to each stage of the `VantaSolve` ritual.
- [Low Priority - runtime/simulation_run.py] Log individual links if 'links' structure becomes detailed (L348).
- [Low Priority - rules/rulesmith.py] Implement rule condition checking logic (L47, L52).
- [Low Priority - rules/rulesmith.py] Implement rule effect execution logic (L58).
- [Low Priority - rules/rulesmith.py] Implement action modification logic based on rules (L65).
- [Low Priority - reasoning/reasoning_module.py] Implement actual reasoning logic (L7).
- [Low Priority - reasoning/reasoning_module.py] Implement goal checking logic (L12).
- [Low Priority - reasoning/reasoning_module.py] Implement exploration/decomposition logic (L17).
- [Low Priority - reasoning/reasoning_module.py] Implement idea generation (e.g., LLM call) (L23).
- [Low Priority - feedback/autotrainer.py] Implement conversion of episodes to training examples (L29).
- [Low Priority - feedback/autotrainer.py] Implement fine-tuning API call (L30).
- [Low Priority - feedback/autotrainer.py] Implement scheduler integration (APScheduler/cron) (L42).
- [Low Priority - external/sandbox_vm.py] Initialize connection to sandbox environment (Docker/Firecracker) (L11).
- [Low Priority - core/vitals_layer.py] Implement logic based on SymbolicCompressor output/metrics (L97).
- [Low Priority - core/vanta_master_core.py] Add checks for engine startup results (L765).
- [Low Priority - core/vanta_master_core.py] Add checks for engine shutdown results (L806).
- [Low Priority - core/vanta_master_core.py] Implement scalable spatial querying for stigmergic field (L914).
- [Low Priority - core/symbolic_compression.py] Add advanced clustering methods (e.g., embeddings) (L72).
- [Low Priority - core/symbolic_compression.py] Add meta-symbol generation for clusters (L74).
- [Low Priority - core/swarm_weave.py] Add cross-agent memory sharing methods (L133).
- [Low Priority - core/swarm_weave.py] Implement decay/pruning for agent buffers (L134).
- [Low Priority - core/sleep_mutator.py] Implement more sophisticated mutation strategies (L147).
- [Low Priority - core/mutation_engine.py] Load configurable keys properly (L46).
- [Low Priority - core/mutation_engine.py] Implement robust nested config key access (L52).
- [Low Priority - core/mutation_engine.py] Implement meaningful content generation (e.g., LLM) (L84).
- [Low Priority - core/mutation_engine.py] Implement sophisticated perturbation logic (L112).
- [Low Priority - core/memory_weave.py] Implement mapping of source branch IDs to snapshot node IDs (L116).
- [Low Priority - core/kernel_manager.py] Handle nested config keys correctly (L19).
- [Low Priority - core/identity_trees.py] Add methods for querying subtrees/common ancestors (L295).
- [Low Priority - core/gating_node.py] Implement sophisticated drift vector analysis (L35).
- [Low Priority - core/gated_breath.py] Integrate expansion logic trigger (L78).
- [Low Priority - core/gated_breath.py] Potentially refine density calculation (L79).
- [Low Priority - app.py] Get mutation chance from config/identity (L151).
- [Low Priority - agents/moerouter.py] Add logic to load other LLMs (e.g., Ollama) (L71).
- [Low Priority - agents/moerouter.py] Implement actual routing logic (L79).
- [Low Priority - agents/proxy_openai_agent.py] Implement backoff/retry for OpenAI calls (L250).
- [Low Priority - agents/fork_handler.py] Implement actual policy-driven branch selection logic (L76).
- [Low Priority - agents/fork_handler.py] Update reason for branch selection (L96).
- [Low Priority - agents/fork_handler.py] Implement merging algorithm (L115).
- [Low Priority - agents/data_unifier_agent.py] Implement actual ML logic for unification (L102).
- [Low Priority - agents/data_unifier_agent.py] Implement query logic against data store (L122).
- [Low Priority - agents/base_agent.py] Add boundary handling for agent movement (L421).
- [Low Priority - agents/base_agent.py] Implement logic for `process_perception` (L458).
- [Low Priority - agents/base_agent.py] Implement calculation for `PurposePulse` (L493).
- [Low Priority - agents/agenda_scout.py] Load roadmap/task list from config (L9).
- [Low Priority - agents/agenda_scout.py] Implement task selection logic (L14).
# --- Added High-Level Completeness & Refinement Tasks ---
- [Medium Priority - Completeness] Implement core VantaMasterCore features (swarm health, purpose pulse, blessing, stigmergic query).
- [Medium Priority - Completeness] Implement internal logic for core engines (Governance, Procedural, Mutation).
- [Medium Priority - Completeness] Verify and complete implementation of all specific agents in vanta_seed/agents/.
- [Medium Priority - Completeness] Verify and complete implementation of memory engines and query logic.
- [Medium Priority - Completeness] Verify and complete main application lifecycle in app.py.
- [Medium Priority - Refinement] Systematically add robust error handling across all modules.
- [Medium Priority - Refinement] Replace all placeholder 'print' statements with standard logging.
# --- Added Missing Task Areas ---
- [Medium Priority - Integration] Define and implement integration patterns for new modules (DataUnifier, Catalog, etc.) within VantaMasterCore (Pilgrim registration, messaging, etc.).
- [Medium Priority - Symbolic Layer] Implement core symbolic constructs (Trinity Swarm dynamics, Memory Relics, WhisperSeeds, Dream Pulses) and ensure alignment in agent behavior.
- [Medium Priority - Testing] Define testing strategy (unit, integration, e2e) and implement baseline test suites for core modules and agents.
- [Medium Priority - Documentation] Add detailed implementation documentation (code comments, READMEs) for core vanta_seed modules and agents.
- [Low Priority - UI Integration] Design and implement API endpoints required for UI/frontend interaction.
- [Low Priority - UI Integration] Develop frontend components and connect to the VANTA backend (if UI is in scope).
- [Low Priority - Deployment] Detail specific cloud configurations, database setup, monitoring setup, and CI/CD pipeline enhancements.
## TODO - Resolve pip-tools compile error for sentence-transformers/vllm

**Context:**
Currently blocked on installing `sentence-transformers` (and its dependency `torch`) and `vllm` due to errors during `pip-tools compile`. The primary goal is to get `sentence-transformers` working for the `RitualCollapseService`.

**Current Issue:**
- Command: `python -m piptools compile -v --resolver=backtracking requirements.in`
- Error: `NotADirectoryError: [WinError 267] The directory name is invalid`
- This error occurs while `pip-tools` is "Getting requirements to build wheel" for the `vllm` package. It's a common Windows issue related to temporary directory paths or path length limitations during package builds.

**Last Attempted Solution & Next Immediate Step:**
1.  **Problem:** Incorrect syntax was used for setting environment variables (`export` in a PowerShell prompt).
2.  **Corrected Approach (To be executed next):**
    *   In the MINGW64 terminal (which is currently showing a PowerShell prompt `PS C:\...`):
        ```powershell
        $env:TEMP = "C:\tmp"
        $env:TMP = "C:\tmp"
        if (-not (Test-Path "C:\tmp")) { New-Item -ItemType Directory -Force -Path "C:\tmp" }
        python -m piptools compile -v --resolver=backtracking requirements.in
        ```
    *   Observe the output of the `pip-tools compile` command.

**If the above still fails, subsequent diagnostic/fix steps:**
1.  **Windows Long Path Support:** Verify if Win32 long paths are enabled on the system. If not, enable it (requires admin and possibly a restart).
    *   Group Policy: `gpedit.msc` -> `Local Computer Policy` -> `Computer Configuration` -> `Administrative Templates` -> `System` -> `Filesystem` -> `Enable Win32 long paths`.
    *   Registry: `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem`, set `LongPathsEnabled` (DWORD) to `1`.
2.  **Isolate `vllm`:** If the error persists and seems specific to `vllm`:
    *   Temporarily comment out `vllm` from `requirements.in`.
    *   Re-run `python -m piptools compile ...` (with `TEMP`/`TMP` set) to see if other dependencies (especially `sentence-transformers` and `torch`) can compile successfully.
    *   This would allow `RitualCollapseService` development to proceed, deferring the `vllm` installation complexities.
3.  **Pin `torch` version (If `sentence-transformers` or `torch` itself causes issues after isolating `vllm`):**
    *   If errors point to `torch` installation (e.g., CUDA version conflicts on Windows), try pinning `torch` to a known compatible CPU-only version or a specific version known to work on Windows in `requirements.in`. Example:
        ```
        torch==2.1.0+cpu # or a specific version indicated by errors
        torchvision==0.16.0+cpu
        torchaudio==2.1.0+cpu
        ```
        (Note: The `+cpu` specifiers might need to be obtained from PyTorch's official site for the correct wheel).

**Goal upon resuming:**
- Successfully run `python -m piptools compile --resolver=backtracking requirements.in -o requirements.txt` to generate a complete `requirements.txt`.
- Successfully run `pip install -r requirements.txt`.
- Successfully run `python -m vanta_seed.services.ritual_collapse_service` without `ModuleNotFoundError` for `sentence_transformers`. 

# --- VANTA Kernel Protocol Automation (Agentic DevOps Standard) ---
- [ ] Integrate `.github/workflows/vanta_kernel_protocol.yml` for scheduled protocol actions (commit graph, trigger registry, RL label generation, dependency audit, security scan)
- [ ] Implement and maintain `scripts/update_protocol_registry.py` and `scripts/generate_rl_labels.py` for auto-generation
- [ ] Ensure `docs/triggers.md` is always up-to-date and auto-generated
- [ ] All protocol and symbolic trigger changes must be validated by scheduled automation
- [ ] This is mandatory for VANTA Kernel, Guardian, InnerCircle, VantaChat
- [ ] Tags: #agentic_devops #protocol_integrity

# --- VANTA Kernel + Cross-App Protocol Trigger System ---
# (As per user specification - requires CoT for prioritization and ownership)

- [ ] **Design & Implement `trigger_registry.py`**:
    - Define universal kernel trigger definitions.
    - Ensure it's app-agnostic, context-aware, and auto-loaded by Trigger Engine.
    - User to define: Priority, Ownership.
- [ ] **Design & Implement `vanta_trigger_engine.py`**:
    - Implement universal trigger resolution logic.
    - Enable module-based execution for different protocols.
    - Support app-level and child-level context.
    - User to define: Priority, Ownership.
- [ ] **Design & Implement `efficacy_score.py`**:
    - Implement RL feedback and decay system.
    - Include time-based decay and caregiver manual override.
    - Integrate with RitualCollapse, MythicRecall, and Trigger Engine.
    - User to define: Priority, Ownership.
- [ ] **Design & Implement `caregiver_roles.yaml` (or `roles.yaml`)**:
    - Define UI/Access Role Binding.
    - Ensure it's a universal access filter, aware of app and Narrative Recall.
    - User to define: Priority, Ownership.
- [ ] **Define Visual Prompt Engine Output Format**:
    - Specify the universal response format for visual prompts (message, animation, emotions).
    - Ensure it's cross-app ready (Guardian, InnerCircle, VantaChat).
    - User to define: Priority, Ownership.
- [ ] **Design & Implement DevOps Auto-Documentation & Training Label Generation**:
    - Auto-register triggers in `THEPLAN.md`.
    - Generate `docs/triggers.md`, `app_triggers/<app_name>.yaml`, and `rl_training_rows.csv`.
    - Ensure it's auto-maintained for continuous RL training batches.
    - User to define: Priority, Ownership.
- [ ] **(Optional - v2) Design & Implement Symbolic Cross-Child Learning**:
    - Utilize `MythicObject.tags` for age, trauma, diagnosis.
    - Enable recall for "what worked for similar cases?"
    - Integrate with VANTA+Guardian combined knowledge recall.
    - User to define: Priority, Ownership.

- [ ] **Chain of Thought (CoT) for Kernel System**:
    - Sequence development priority for the above modules.
    - Recommend module ownership structure.
    - Generate initial development stubs where appropriate (after dependency resolution). 