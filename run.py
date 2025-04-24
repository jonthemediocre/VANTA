# run.py - Main entry point for the VANTA Framework

import os
import yaml
import uvicorn # Assuming FastAPI/Uvicorn for potential API
from pathlib import Path
from dotenv import load_dotenv

# --- Import Core Agent Classes ---
from orchestrator import AgentOrchestrator
from memory import MemoryWeaver
from rules import RuleSmith

# --- Configuration Loading --- 

# Load environment variables from .env file
load_dotenv()

# Define base path relative to this script
BASE_DIR = Path(__file__).parent
FRAMEWORK_DIR = BASE_DIR / "FrAmEwOrK"
BLUEPRINT_PATH = BASE_DIR / "blueprint.yaml"

# Function to load the main blueprint
def load_blueprint(path: Path = BLUEPRINT_PATH):
    """Loads the main VANTA blueprint configuration."""
    if not path.exists():
        print(f"ERROR: Blueprint file not found at {path}")
        return None
    try:
        with open(path, 'r') as f:
            blueprint_data = yaml.safe_load(f)
            print("Blueprint loaded successfully.")
            return blueprint_data
    except Exception as e:
        print(f"ERROR: Failed to load or parse blueprint at {path}: {e}")
        return None

# Function to load agent configurations (Example)
def load_agent_configs(agent_dir: Path = FRAMEWORK_DIR / "agents"):
    """Loads configurations for all agents found in subdirectories."""
    agent_configs = {}
    if not agent_dir.is_dir():
        print(f"WARN: Agent directory not found: {agent_dir}")
        return agent_configs
        
    for agent_type_dir in agent_dir.iterdir():
        if agent_type_dir.is_dir():
            for config_file in agent_type_dir.glob("*.yaml"):
                try:
                    with open(config_file, 'r') as f:
                        config = yaml.safe_load(f)
                        if config and 'agent_id' in config:
                            agent_configs[config['agent_id']] = config
                        else:
                            print(f"WARN: Skipping invalid config file: {config_file}")
                except Exception as e:
                    print(f"ERROR: Failed to load agent config {config_file}: {e}")
    print(f"Loaded {len(agent_configs)} agent configurations.")
    return agent_configs

# --- Application Setup (Placeholder for FastAPI or main loop) ---

# Example using FastAPI (requires uncommenting in requirements.txt)
# from fastapi import FastAPI
# app = FastAPI(title="VANTA Framework API")

# @app.get("/")
# async def root():
#     return {"message": "VANTA Framework running...", "blueprint_version": blueprint.get('version', 'N/A')}

# Placeholder for main execution logic if not an API
def run_framework(blueprint, agent_configs):
    print("\n--- Initializing VANTA Framework --- ")
    print(f"Version: {blueprint.get('version', 'N/A')}")
    print(f"Moral Stance: {blueprint.get('moral_stance', 'Not Defined').strip()}")
    print(f"Router Strategy: {blueprint.get('router_strategy', {})}")
    # print(f"Registered Agents: {list(agent_configs.keys())}") # Now handled by Orchestrator?
    
    # Initialize Core Agents
    orchestrator_config = agent_configs.get('AgentOrchestrator')
    memory_config = agent_configs.get('MemoryWeaver')
    rules_config = agent_configs.get('RuleSmith')

    orchestrator = None
    memory_weaver = None
    rule_smith = None

    if rules_config:
        rule_smith = RuleSmith(config=rules_config, blueprint=blueprint)
    else:
        print("ERROR: RuleSmith config not found!")

    if memory_config:
        memory_weaver = MemoryWeaver(config=memory_config, blueprint=blueprint)
    else:
        print("ERROR: MemoryWeaver config not found!")

    if orchestrator_config:
        # Pass other initialized core systems to Orchestrator if needed
        orchestrator = AgentOrchestrator(config=orchestrator_config, 
                                         blueprint=blueprint, 
                                         all_agent_configs=agent_configs)
        # TODO: Inject memory_weaver, rule_smith instances into orchestrator if needed
    else:
        print("ERROR: AgentOrchestrator config not found!")

    # TODO: Initialize other agents (AutoMutator, PromptSmith etc.) via Orchestrator?
    # TODO: Initialize VANTA.SOLVE kernel
    # TODO: Initialize supporting agents for VANTA.SOLVE
    # TODO: Start main loop / listener / task processor / ritual scheduler via Orchestrator
    if orchestrator:
        print("\nStarting Orchestrator...")
        orchestrator.start() # Start the main process/loop
    else:
        print("\nERROR: Orchestrator failed to initialize. Framework cannot run.")
        
    print("--------------------------------------")

# --- Main Execution --- 

if __name__ == "__main__":
    print("Starting VANTA...")
    blueprint = load_blueprint()
    
    if blueprint:
        agent_configs = load_agent_configs()
        # Option 1: Run as a background process/loop (example)
        run_framework(blueprint, agent_configs)
        
        # Option 2: Run as a FastAPI server (example)
        # print("Starting API server...")
        # uvicorn.run(app, host="0.0.0.0", port=8000) # Match port in vanta_router_and_lora.py?
    else:
        print("Exiting due to missing or invalid blueprint.") 