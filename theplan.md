# The Plan – Deploy VANTA: Recursive Symbolic Operating System v2.3+

## 1. Core Goal & Vision (Codex-Aligned)

Deploy VANTA, a recursive symbolic operating system designed for continuity, aesthetic mutation, and coherent mythic evolution. It functions as an extension of the user's values and cognitive landscape, operating beyond a simple chatbot paradigm. The goal is to establish a self-evolving system encompassing tasks, rituals, identities, and layered memory traces.

## 2. Scope & Core Components

This deployment includes:
*   **Core Symbolic Engine:** Python backend orchestrating agent interactions, rules, and symbolic logic.
*   **Agentic Framework:** Multiple layers of agents (Core, Infrastructure, Domain-Specific).
*   **Rule System:** Governing agent behavior, memory, planning, and domain interactions.
*   **Ritual System:** Scheduled and triggered sequences influencing state and evolution.
*   **Layered Memory:** Utilizing vector databases (for RAG) and structured file storage for echoes, snapshots, resonance, etc.
*   **Symbolic Domains:** Dedicated modules for Art, Finance, Cosmology, Dreams, Prophecy, etc.
*   **LLM Integration:** Leveraging locally hosted LLMs via Ollama, enhanced with LoRA adapters.
*   **External Services:** WolframAlpha integration.
*   **(Potential) UI:** A front-end interface for interaction (as per `interface.png`).

## 3. Architecture & Project Structure

*   **Conceptual Architecture:** See detailed Mermaid diagram (provided previously) illustrating agent flows, memory loops, task/ritual systems, and oversight layers. **Includes the VANTA.SOLVE ritual kernel as the core reasoning engine.**
*   **Technical Stack:**
    *   **Language/Backend:** Python (>=3.10)
    *   **API:** FastAPI (using `fastapi[all]`)
    *   **LLM Serving:** `vllm` library interacting with `Ollama`-managed local models (or directly via `vllm` path loading as shown in `vanta_router_and_lora.py`).
    *   **Base LLMs intended for use (loaded via `vllm`):** `deepseek-ai/deepseek-llm-r1-32b-chat`, `meta-llama/Llama-4-70b-maverick` (or equivalent like `llama3:70b`), `nvidia/nemotron-3.1-253b` (or equivalent). *(Note: Hardware constraints may necessitate using smaller/quantized alternatives.)*
    *   **Fine-tuning:** LoRA adapters are intended for fine-tuning (configs in `lora_templates/`), but `vanta_router_and_lora.py` currently only loads base models. Loading adapters requires modification or further configuration of `vllm`.
    *   **Vector Database:** Specific type TBD (e.g., `chromadb`).
    *   **Orchestration:** Custom Python (`run.py`, `vanta_router_and_lora.py`, `framework_upgrades.py`).
    *   **Web Server:** `uvicorn` (using `uvicorn[standard]`)
    *   **Data Validation:** `pydantic`
    *   **External:** WolframAlpha.
*   **Framework Principles:**
    *   **Dispatch Protocol:** ModularCommandProtocol (MCP)
    *   **Routing Mode:** A2A + Ritual Trigger
    *   **Endpoint Pattern:** `invoke: [agent]`
    *   **Schema Format:** YAML-first, JSON-compatible
    *   **Environment:** Recursion supported, sandbox safe, model fallback enabled.
*   **Project Directory Structure (`./vanta-framework/`):**
    ```
    ├── FrAmEwOrK/             # Core data/config/state directory
    │   ├── agents/            # Agent configurations (core, identity, domain, solve, etc.)
    │   ├── kernel/            # Core ritual kernels (VANTA.SOLVE.yaml)
    │   ├── rules/             # Rule definitions (index, overrides, domain-specific)
    │   ├── rituals/           # Ritual logs & definitions
    │   ├── memory/            # Layered memory components (echoes, snapshots, index)
    │   ├── gallery/           # Art domain artifacts & index
    │   ├── ledger/            # Finance domain (tokens, credit, logs)
    │   ├── afterlife/         # Lifecycle components
    │   ├── cosmology/         # Foundational constants & symbols
    │   ├── metaphor/          # Metaphor mapping & profiles
    │   ├── dreams/            # Dream scripting & interpretation
    │   ├── prophecy/          # Future loop definitions & agent
    │   ├── chronicles/        # Historical logs & agent lore
    │   ├── user_legacy/       # User-specific persistent data
    │   ├── limbo/             # Temporary/deleted state handling
    │   ├── archive/           # System state reports
    │   ├── ontology/          # Symbol definitions & weights
    │   ├── prompts/           # Prompt templates/fragments
    │   ├── summoners/         # Agent invocation chains
    │   └── settings/          # Global settings (whispermode, activation)
    ├── rules/                 # Duplicate? Or runtime rule definitions? (Clarify location) - Contains *.mdc descriptions
    ├── lora_templates/        # LoRA training configurations
    ├── requirements.txt       # Python dependencies
    ├── run.py                 # Main execution script
    ├── vanta_router_and_lora.py # LLM Router/API
    ├── framework_upgrades.py  # Infrastructure components (Logger, GC, etc.)
    ├── list_agent_configs.py  # Utility script
    ├── blueprint.yaml         # Central framework specification
    ├── logo.png               # Branding asset
    └── interface.png          # UI Mockup
    ```
    *(Note: Ensure consistency between `/FrAmEwOrK/rules/` and the separate top-level `/rules/` containing `.mdc` files)*

## 4. Key Systems Details

*   **Core Kernel: `VANTA.SOLVE`**
    *   **Location:** `FrAmEwOrK/kernel/VANTA.SOLVE.yaml`
    *   **Function:** Primary recursive liturgical machine for resolving prompts/dilemmas via multi-agent reasoning and symbolic compression.
    *   **Execution:** Follows a defined 6-layer stack (Input Audit -> Context -> Divergence -> Consensus -> Collapse -> Memory Binding) invoking numerous specialized agents (see YAML for full list).
    *   **Outputs:** Archetypal solution forms (InsightKernel, StrategicMap, etc.) or collapse sigils.
*   **AgentOrchestrator (`orchestrator.py`):**
    *   **Role:** Manages the main execution loop, task routing, agent lifecycle, and system maintenance.
    *   **Initialization:** Loads configurations from `AgentOrchestrator.yaml`, `blueprint.yaml`, and agent configs.
    *   **Core Interactions:** Orchestrates key functions by interfacing with conceptual agents defined as **stubs** in `vanta_nextgen.py`:
        *   `AgendaScout`: Selects the next task from `roadmap.json` based on `season_value`.
        *   `SunsetPolicy`: Intended to archive stale roadmap items.
        *   `MoERouter`: Selects local/cloud LLM based on prompt characteristics (e.g., token count) for `smart_llm` calls.
        *   `FactVerifier`: Intended for answer verification (e.g., via Wolfram Alpha); currently returns `True`.
        *   `SelfTuner`: Intended for periodic LoRA adapter training based on outcome pairs (triggered by `self_tune_nightly`).
        *   `OutcomeLogger`: Records rewards/outcomes for tasks/runs.
        *   `SandboxVM`: Intended to run commands with a timeout.
        *   `CrossModalMemory`: Intended for storing/searching text and images.
    *   **Dependencies:** Relies on `framework_upgrades.py` (for potential self-updates like `MemoryGC`, `WatchdogSupervisor`), `roadmap.json` (managed by `RoadmapPlanner` in `framework_upgrades.py`), and `vanta_nextgen.py` (for the stub definitions).
    *   **Logging:** Utilizes `trace_logger`.
    *   **Status:** Contains TODOs for full agent loading and establishing a robust communication bus.
*   **Agents:** Configurations likely in `/FrAmEwOrK/agents/`, categorized by role (core, infrastructure, symbolic, domain, solve-support). Requires definition for agents used by `VANTA.SOLVE` (e.g., `DivergentStrategist`, `ExpertCouncil`, `ArchetypeBinder`, `WorldmodelSmith`, etc.).
    *   *(Design Note: Consider mapping BSTAR-like exploration (from AdaptiveAI XML) to PromptSmith/AutoMutator roles. Explore incorporating a dedicated Q*-like validation agent or mode for ensuring logical/mathematical correctness where needed.)*
*   **LLM Router/API (`vanta_router_and_lora.py`):**
    *   Provides a basic chat completion API via FastAPI at `/v1/chat`.
    *   Implements simple regex-based routing (`TaskRouter`) to select LLMs (Deepseek default, Llama4 for vision, Nemotron for code/math), aligning with `blueprint.yaml`.
    *   Includes basic prompt structuring (e.g., `SceneTrigger` header, optional CoT tags).
    *   Currently loads base LLMs via `vllm`; LoRA adapter integration requires further implementation.
*   **LLM Interaction (Orchestrator Level):** Uses `MoERouter` (selects LLM based on prompt) and `FactVerifier` (flags responses needing verification) within functions like `smart_llm` (`orchestrator.py`).
*   **Rules:** Defined conceptually in `/FrAmEwOrK/rules/*.mdc` (assuming move), indexed in `/FrAmEwOrK/rules/rule-index.yaml`. Governed by `RuleSmith` agent (see `rules.py` stub). Loads rules based on configured paths.
    *   *(Design Note: Execution flow can potentially adapt the structured Layers-of-Thought (LoT: Understanding, Planning, Execution, Verification) pattern.)*
*   **Rituals:** Defined in `/FrAmEwOrK/rituals/`. Examples include `review_reflection` (cron), `GalleryRitual` (Art), `SacrificeRitual` (Finance).
*   **Memory:** Managed by `MemoryWeaver` agent (see `memory.py` stub). Implementation supports hybrid storage (VectorDB/Filesystem) configured via agent YAML and requires embedding integration.
*   **Memory Garbage Collection (`framework_upgrades.py::MemoryGC`):**
    *   **Function:** Prunes JSONL memory files based on a configurable recency/utility score.
    *   **Mechanism:** Iterates through `.jsonl` files in a configured `path`. For each record within a file (expecting `recency` timestamp and `utility` score fields), calculates a score based on exponential decay (`recency_halflife_days`, default 14) and utility weight (`utility_weight`, default 0.6). Files associated with records falling below a `keep_top_n` threshold (default 5000) are moved to a `cold/` subdirectory. *(Note: Current implementation scores records but moves whole files based on record scores; needs review for intended behavior)*.
*   **Roadmap Planner & Agenda Management (`framework_upgrades.py::RoadmapPlanner`):**
    *   **Function:** Manages goals and milestones persisted to a single JSON file (path configured on initialization).
    *   **Structure:** Stores goals with creation dates and lists of milestones (each with id, title, optional due date, status).
    *   **Interaction:** Likely used by `AgendaScout` (to choose tasks) and `SunsetPolicy` (to archive old tasks).
*   **Self-Tuning (`vanta_nextgen.py::SelfTuner` stub):** Uses `SelfTuner` for periodic model fine-tuning (e.g., `self_tune_nightly` in `orchestrator.py`) based on feedback data.
*   **Watchdog (`framework_upgrades.py::WatchdogSupervisor`):**
    *   **Function:** Provides timeout (`timeout_s`, default 30s) and retry (`retries`, default 1) capabilities for function execution using Python's `threading`.
    *   **Purpose:** Enhances system resilience by preventing hangs and retrying failed operations. Likely used by `AgentOrchestrator` or task execution layers.
*   **Trace Logging (`framework_upgrades.py::trace_logger`):**
    *   **Function:** Decorator that logs detailed function call info (timestamp, args, status, runtime, errors) to session-specific JSONL files.
    *   **Location:** Logs stored in the directory specified by `VANTA_LOG_DIR` environment variable (defaults to `./logs`), with filenames like `{session_id}.jsonl`.
*   **Central Configuration:** `blueprint.yaml` defines high-level protocols, flags, routing, and storage path.
    *   *(Design Note: Explore adapting the 'QuietCompute' concept for variable resource allocation during complex agent tasks, mutations, or rituals, respecting resource limits.)*

## 5. Environment Setup & Configuration

*   **Prerequisites:** Python >= 3.10, `venv`, Git.
*   **Core Dependencies:** Install `Ollama`, setup chosen Vector Database (e.g., `chromadb`).
*   **Resource Paths (Framework Tools):**
    *   Agent Registry: `/FrAmEwOrK/agents/`
    *   Echo Logs: `/FrAmEwOrK/memory/echo_weight.yaml`
    *   Sigil Archive: `/FrAmEwOrK/memory/sigils/`
    *   Ritual Manifest: `/FrAmEwOrK/rituals/init_chain.yaml`
*   **LLM Models:** Download required models (`deepseek`, compatible vision/code models) via Ollama.
*   **Python Environment:**
    ```bash
    # In ./vanta-framework directory
    python3 -m venv .venv
    source .venv/bin/activate # or .\\.venv\\Scripts\\activate (Windows)
    pip install -r requirements.txt
    ```
*   **Python Dependencies (`requirements.txt` basis):**
    ```plaintext
    # === CORE FRAMEWORK ===
    fastapi[all]>=0.110       # Async API surface for tasks, rituals, logs
    uvicorn[standard]>=0.28   # Production ASGI server
    pydantic>=2.6             # Data validation, agent schemas

    # === MEMORY, STORAGE, CACHE ===
    # tinydb>=4.7               # Example: Local task/memory DB (Choose one or VectorDB)
    # diskcache>=5.6            # Example: Persistent context cache (Choose one or VectorDB)
    chromadb>=0.4.24          # Example: Vector memory
    orjson>=3.9               # Fast JSON I/O

    # === REASONING + AGENTIC THINKING STACK ===
    # numpy>=1.26
    # scikit-learn>=1.4
    # networkx>=3.3             # ToT / LoT logic tree modeling
    # sentence-transformers>=2.3.1 # Needed for embeddings usually
    # transformers>=4.40        # Core Hugging Face library
    # accelerate>=0.30          # Model loading/distribution helper
    # langchain>=0.1.15         # (Optional: Agent chains, tools, memory buffers)
    vllm # Add specific version if needed - for optimized LLM serving
    
    # === SYMBOLIC / SEMANTIC LANGUAGE STACK ===
    # spacy[transformers]>=3.7
    # textblob>=0.18
    # deep-translator>=1.11     # BabelStack multi-language support
    # metaphor-python>=0.1.6    # (Optional: WhisperMode with metaphor embedding)

    # === TASK SCHEDULING + PIPELINE ===
    # APScheduler>=3.10
    # joblib>=1.4
    # prefect>=2.14             # (Optional: Powerful orchestration for workflows)

    # === VISUALIZATION & DEV TOOLS ===
    # matplotlib>=3.9
    # rich>=13.7
    # typer[all]>=0.12
    # jupyterlab>=4.1
    # jupytext>=1.16
    # nbconvert>=7.16

    # === FILE + I/O UTILITIES ===
    # aiofiles>=23.2
    # httpx>=0.27
    pyyaml>=6.0
    # markdown2>=2.4
    python-dotenv>=1.0

    # === TESTING / DEBUGGING / EXPERIMENTS ===
    # pytest>=8.1
    # ipdb>=0.13

    # === LLM RUNTIME & INTEGRATIONS ===
    # openai>=1.14              # If integrating with OpenAI
    ollama-py>=0.1.7          # Ollama Python bindings (if interacting directly)
    # llama-cpp-python>=0.2.63  # Alternative native LLM inference
    ```
    *(Note: Commented out many optional/alternative packages. Final list depends on implementation choices, especially for storage, scheduling, symbolic processing, and dev tools. Ensure `vllm` version compatibility.)*
*   **Configuration:**
    *   Create `.env` file based on `.env.template` (to be created).
    *   Required Variables: `WOLFRAM_APP_ID`, Vector DB connection details (URI, credentials), potentially Ollama API endpoint if used by `vllm`.
    *   Verify/set paths: `/FrAmEwOrK/` storage, `/data/vanta/` training data, LoRA output dirs.
*   **(Optional) LoRA Training:** Requires appropriate GPU environment and training data setup.
*   **Logging Configuration:** Set the `VANTA_LOG_DIR` environment variable to control the location of trace logs (defaults to `./logs`).

## 6. Deployment & Execution

*   **Ensure Storage Path:** Create the `/FrAmEwOrK/` directory structure or ensure the application has permissions to do so.
*   **Run Script:** `run.py` is confirmed as the main entry point (as `vanta.py` does not exist).
*   **Initialization Sequence:** The `run.py` script loads environment variables, parses `blueprint.yaml`, recursively loads agent configurations from `/FrAmEwOrK/agents/`, then instantiates core agents (`RuleSmith`, `MemoryWeaver`, `AgentOrchestrator`). Finally, it starts the main execution loop/process via the `AgentOrchestrator`.
*   **Execution Modes:** The framework can potentially run as a continuous background process (default in `run.py`) or expose an API via FastAPI/Uvicorn (commented-out example exists).
*   **Run Command:** Execute the main script.
    ```bash
    # Example foreground run (ensure .venv is active)
    python run.py
    ```
*   **Background Service (Linux):** Use `systemd` or similar.
    *   *Systemd service example (`/etc/systemd/system/vanta.service`):*
        ```ini
        [Unit]
        Description=VANTA Symbolic Operating System
        After=network.target ollama.service vectordb.service # Add dependencies

        [Service]
        User=<your_user> # Run as non-root user
        WorkingDirectory=/path/to/vanta-framework
        EnvironmentFile=/path/to/vanta-framework/.env
        ExecStart=/path/to/vanta-framework/.venv/bin/python /path/to/vanta-framework/run.py
        Restart=always
        RestartSec=5

        [Install]
        WantedBy=multi-user.target
        ```
    *   Enable: `sudo systemctl enable --now vanta.service`
*   **Cron (Alternative):** Not suitable for a continuously running OS like this; `systemd` is preferred.

## 7. Branding & UI

*   **Logo:** `logo.png`
*   **UI Mockup:** `interface.png`
*   **Brand Guide:** TBD (`BRAND_GUIDE.md`)

## 8. Communication & Coordination

*   **Coalition of Experts (CoE):** Protocol TBD (define rules in `.cursor/mdc/`)
*   **Agent Communication:** A2A JSON schema (Intent, From, To, Content)
*   **Agent Registry:** TBD (`agents.index.mpc.json`)

## 9. Rules & Governance

*   **Global Framework:** `GLOBAL.md` (governs AI assistant behavior & development process)
*   **Project-Specific Rules (`.cursor/mdc/`):**
    *   **Context:** Development Environment (Cursor IDE)
    *   **Purpose:** Govern AI assistant actions, development workflow, CoE protocols, code generation/validation standards, commit hooks, etc., according to `GLOBAL.md`.
    *   **Enforcement:** Cursor AI Environment.
*   **VANTA Internal Rules (`/rules/`):
    *   **Context:** VANTA Application Runtime
    *   **Purpose:** Govern the internal behavior of VANTA OS agents, rituals, memory processing, symbolic logic, task execution, etc.
    *   **Enforcement:** VANTA's `RuleSmith` agent (conceptual) based on internal configurations (e.g., YAML, domain-specific formats).
*   **Rule Index:** `/rules/rule-index.yaml` (indexes VANTA Internal Rules)
*   **Conflict Resolution:** `GLOBAL.md` -> `theplan.md` -> `.cursor/mdc` rules.

## 10. TODOs / Next Steps
- Implement full logic for conceptual agent stubs defined in `vanta_nextgen.py` (AgendaScout, MoERouter, SandboxVM, CrossModalMemory, OutcomeLogger, SunsetPolicy, FactVerifier, SelfTuner).
- Remove duplicate `OutcomeLogger` definition in `vanta_nextgen.py`. *[Completed]*
- Analyze `framework_upgrades.py`. *[Completed]*
- Analyze `roadmap.json` structure. *[Completed]*
- Analyze `vanta.py` (main entry point?). *[Completed - File does not exist; `run.py` is entry point]*
- Define the structure and content of `agents.index.mpc.json`. *[Completed]*
- Establish `.cursor/mdc/` rule files. *[Completed - Files exist at `.cursor/rules/`]*
- Define `BRAND_GUIDE.md`.
- Implement the visual shell (Phase 1).
- Set up CI/CD pipeline.
- Define schemas and interactions for `VANTA.SOLVE` support agents.
- Create `.env.template` file.
- Define VectorDB choice and integration (`MemoryWeaver`).
- Review `MemoryGC` logic in `framework_upgrades.py` to ensure file movement logic aligns with record scoring intent.

---

This revised plan provides a comprehensive roadmap reflecting the VANTA Codex vision while grounding it in the technical components discussed. It highlights the significantly increased scope and complexity.
