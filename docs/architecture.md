# VANTA Architecture

This document outlines the high-level architecture of the VANTA agent framework.

## 1. System Overview

```mermaid
flowchart TD
  subgraph Simulation Loop (simulation_run.py)
    A[Start Simulation] --> A1[Load Oath of Becoming]
    A1 --> B{Interaction Loop}

    B --> C[Load Identity & Config]
    C --> D{Breath Cycle Check}
    
    D -- Cycle < 10 --> E[Destiny Check]
    D -- Cycle = 10 --> F[Breath Cycle Event]

    F --> FE[Breath Expansion Ritual]
    FE --> G[Memory Echo Trigger]
    
    subgraph Echo Logic
      G --> G1{FTS Results?}
      G1 -- Yes --> G2[Pick random from FTS hits]
      G1 -- No  --> G3[Pick random from full JSONL]
      G2 --> H
      G3 --> H
    end
    
    H[Whisper Echo (whispermode_styler)] --> E

    E --> I[Process Input]
    I --> J[Save Interaction]
    J --> J1[Update FTS Index]
    J1 --> J2[Update Bias Weights]

    J2 --> K[Select Realm (Mythos/Logos)]
    K --> L[Select Reasoning Mode]
    L --> M[Generate Response]
    M --> N[Mutation Ritual Check]
    N --> O[Output Response]
    O --> B

    %% Fractal Growth every N breaths
    F --> P[Fractal Growth Trigger (Every 10 Breaths)]
    P --> Q[Load All Memories (fractal_memory_engine)]
    Q --> R[Create Fractal Links]
    R --> S[Save Fractal Map]
    S --> E
  end

  subgraph Disconnected / CLI Tools
    T[fractal_query.py] -- queries --> U[fractal_memory_map.yaml]
    V[memory_query.py]  -- queries --> W1[*.jsonl] & W2[memory_index.db]
  end

  subgraph Storage
    J --> W1
    J1 --> W2
    S  --> U
  end

  style T fill:#f9f,stroke:#333,stroke-width:2px
  style V fill:#f9f,stroke:#333,stroke-width:2px
```

The VANTA system is designed as a modular, agent-based framework coordinated by a central orchestrator. It leverages layered memory and configurable agents to perform complex tasks.

## 2. Core Components

*(Placeholder: Detail the main building blocks)*

- **Agent Orchestrator (`orchestrator.py`)**: The central coordinator responsible for receiving tasks, routing them to appropriate agents based on configuration and context, managing agent lifecycles, and potentially handling task dependencies.
- **Agents (`agents/`)**: Specialized modules designed to perform specific tasks (e.g., `ImageGeneratorAgent`, `ReflectorAgent`). Each agent has its own configuration (`.json`) and implementation (`.py`).
- **Cross-Modal Memory (`vanta_nextgen.py` - `CrossModalMemory` class)**: Handles the storage and retrieval of different data types (text, images, potentially others) in a persistent manner. *(Placeholder: Specify storage backend, e.g., filesystem, vector DB)*.
- **Configuration (`*.json`, `*.mpc.json`)**: Defines agent behavior, registry, triggers, and system settings.
- **Schemas (`schemas/`)**: JSON schemas defining data structures like agent configurations and task data.

## 3. Agent Types Distinction

It's important to distinguish between two potential types of "agents" in this project's context:

1.  **Backend Agents (`agents/` directory):**
    *   These are the core Python classes (e.g., `ImageGeneratorAgent`, `ReflectorAgent`) managed by the `AgentOrchestrator`.
    *   They run as part of the main VANTA application logic.
    *   They communicate via the `task_data` schema and interact with core components like `CrossModalMemory`.
    *   Their configuration and registry are primarily managed via `.json` files in the `agents/` directory and `agents.index.mpc.json`.

2.  **IDE-Level Agents (`.cursor/agents/` directory - *Optional/Potential*):**
    *   These agents, if implemented (like `agent_base.py` suggests), would run *directly within the Cursor IDE*.
    *   They interact with the IDE's context (current file, diffs, user selections) using protocols like the one defined in `.cursor/agents/agent_base.py`.
    *   They are typically used for providing direct editor assistance (e.g., custom linters, context-aware code actions, inline suggestions) rather than backend task processing.
    *   These are distinct from the backend agents and do not directly interact with the `AgentOrchestrator` unless a specific bridge is built.

This architecture document primarily focuses on the **Backend Agents** and their orchestration.

## 4. Technology Stack

*(Placeholder: List key libraries and technologies)*

- **Language**: Python 3.10+
- **Core Libraries**: *(Add libraries like requests, potentially FastAPI if building an API)*
- **Data Handling**: JSON, YAML
- **Potential Future**: Vector Database (e.g., ChromaDB, Pinecone), Workflow Orchestrator (e.g., Prefect)

## 5. Data Flow Example

*(Placeholder: Trace a sample request, e.g., image generation)*

1.  User Request (e.g., via API or CLI) triggers task creation.
2.  Task (`intent='generate_image'`, `payload={'prompt': '...'}`) added to `AgentOrchestrator` queue.
3.  Orchestrator routes task to `ImageGeneratorAgent`.
4.  `ImageGeneratorAgent` calls external API.
5.  `ImageGeneratorAgent` saves result to `CrossModalMemory`.
6.  Agent returns result (e.g., image ID) to Orchestrator.
7.  Orchestrator returns result to user/caller.

## 6. Design Decisions & Rationale

*(Placeholder: Document key choices, e.g., choice of orchestrator pattern, memory strategy)* 