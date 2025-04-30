# VANTA Modular Agentic FrAmEwOrK (Export 2025-04-22)

This archive contains:

* **framework_upgrades.py** – Trace‑Logger, Watchdog, RoadmapPlanner, MemoryGC
* **vanta_nextgen.py** – AgendaScout, MoERouter, SelfTuner, SandboxVM, etc.
* **orchestrator.py** – Scheduler glue layer
* Skeleton folders for core agents, rules, rituals, tasks, settings, and user profile

Edit the placeholder YAML files to suit your production rules and agents.

## Setup

It is highly recommended to use a dedicated Python virtual environment for this project to avoid dependency conflicts.

1.  **Create a Virtual Environment (if you don't have one):**
    ```bash
    # In the project root directory
    python -m venv .venv 
    ```
    *(Replace `.venv` with your preferred environment name if desired)*

2.  **Activate the Environment:**
    *   **Windows (PowerShell):**
        ```powershell
        .\.venv\Scripts\Activate.ps1
        ```
    *   **Windows (Command Prompt):**
        ```cmd
        .\.venv\Scripts\activate.bat
        ```
    *   **Linux/macOS (bash/zsh):**
        ```bash
        source .venv/bin/activate
        ```
    *(You should see the environment name, like `(.venv)`, appear at the beginning of your terminal prompt)*

3.  **Install Dependencies:**
    ```bash
    # Ensure your virtual environment is active
    pip install -r requirements.txt
    ```

## Running the Orchestrator

1.  Ensure your virtual environment is activated.
2.  Set required API keys in a `.env` file (e.g., `OPENAI_API_KEY=your_key`).
3.  Run the orchestrator:
    ```bash
    python orchestrator.py
    ```

## Using the CLI

1.  Open a *separate* terminal window.
2.  Ensure your virtual environment is activated in this new terminal.
3.  Run commands:
    ```bash
    python cli.py <command> [arguments...]
    ```
    *(See `python cli.py --help` for available commands)*

## Myth Collapse Endpoint

This endpoint merges multiple myth entries into a unified archetype narrative.

### POST /v1/myth/collapse

**Request Body** (application/json):
```json
{  
  "entry_ids": ["mythbranch-xxxx","mythdrift-yyyy"]  
}
```

**cURL**:
```bash
curl -X POST http://localhost:8002/v1/myth/collapse \
  -H "Content-Type: application/json" \
  -d '{"entry_ids":["mythbranch-xxxx","mythdrift-yyyy"]}'
```

**PowerShell**:
```powershell
$body = '{"entry_ids":["mythbranch-xxxx","mythdrift-yyyy"]}'
Invoke-RestMethod -Uri http://localhost:8002/v1/myth/collapse -Method POST -ContentType "application/json" -Body $body
```

**Successful Response** (200 OK):
```json
{
  "collapse_narrative": "<merged narrative text>",
  "model_used": "deepseek-llm:latest",
  "new_entry_id": "mythcollapse-xxxxxxxxxx",
  "symbols": ["Symbol1","Symbol2",...],
  "lineage": {"origin_id":"mythcollapse-xxxxxxxxxx","parent_id":null,"drift_step":0}
}
```

---
