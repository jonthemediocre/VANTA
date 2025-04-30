# run.py - Main entry point for the VANTA Framework

import os
# --- Remove direct env var/config loading ---
# import yaml 
# import uvicorn 
# from pathlib import Path
# from dotenv import load_dotenv
# import json
# -----------------------------------------
import asyncio
import uuid
import yaml # Keep yaml for blueprint loading
from pathlib import Path # Keep Path
import json # <-- Add json import back
import logging # Added for detailed logging

# --- Import centralized config FIRST --- 
import config # This will load .env, set up logging, define paths
# ---------------------------------------

# --- Import the NEW Seed Orchestrator --- 
from vanta_seed.core.seed_orchestrator import AgentOrchestrator 
# --- Comment out OLD orchestrator import ---
# from orchestrator import AgentOrchestrator 
# ----------------------------------------

# --- Configuration Loading (Now handled by config.py) ---

# # --- Set Environment Variables Early --- 
# BASE_DIR = Path(__file__).parent # Defined in config.py
# os.environ["VANTA_LOG_DIR"] = str(BASE_DIR / "logs") # Set in config.py
# print(f"VANTA_LOG_DIR set to: {os.environ['VANTA_LOG_DIR']}") # Printed in config.py
# # -------------------------------------
# 
# # Load environment variables from .env file (can override VANTA_LOG_DIR if present in .env)
# load_dotenv() # Done in config.py

# --- Use paths from config module --- 
# BASE_DIR = Path(__file__).parent
# BLUEPRINT_PATH = BASE_DIR / "blueprint.yaml"
# AGENT_INDEX_PATH = BASE_DIR / "agents.index.mpc.json" 
# -----------------------------------

# Configuration Loading
CONFIG_DIR = Path(__file__).parent / "config"
BLUEPRINT_FILE = CONFIG_DIR / "BLUEPRINT.yaml"
AGENT_INDEX_FILE = CONFIG_DIR / "agents.index.mpc.json"

# Setup Logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.StreamHandler() # Add file handler later if needed
    ]
)
logger = logging.getLogger(__name__)

def load_yaml_config(file_path: Path) -> dict | None:
    """Loads a YAML configuration file."""
    if not file_path.exists():
        logger.error(f"Configuration file not found: {file_path}")
        return None
    try:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading YAML file {file_path}: {e}", exc_info=True)
        return None

def load_json_config(file_path: Path) -> dict | None:
    """Loads a JSON configuration file."""
    if not file_path.exists():
        logger.error(f"Configuration file not found: {file_path}")
        return None
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON file {file_path}: {e}", exc_info=True)
        return None

# --- OLD Agent Orchestrator Logic (Commented Out/Replaced) ---
# from orchestrator import AgentOrchestrator # Old orchestrator
# 
# def initialize_framework(blueprint: dict, agent_definitions: dict) -> AgentOrchestrator:
#     """Initializes the agent framework."""
#     logger.info("Initializing Agent Framework...")
#     orchestrator = AgentOrchestrator(blueprint, agent_definitions)
#     logger.info("Agent Framework Initialized.")
#     return orchestrator
# 
# async def run_framework(orchestrator: AgentOrchestrator):
#     """Runs the main processing loop of the agent framework."""
#     logger.info("Starting Agent Framework Processing Loop...")
#     await orchestrator.run_processing_loop()
#     logger.info("Agent Framework Processing Loop Finished.")
# --- END OLD Logic ---

def initialize_seed_orchestrator(blueprint: dict, agent_definitions: dict) -> AgentOrchestrator:
    """Initializes the VANTA Seed Core Orchestrator."""
    logger.info("Initializing VANTA Seed Core (Unified AgentOrchestrator)...")
    # Pass both blueprint and agent definitions to the unified orchestrator
    orchestrator = AgentOrchestrator(blueprint=blueprint, all_agent_definitions=agent_definitions, config=blueprint)
    logger.info("VANTA Seed Core Initialized.")
    return orchestrator

async def run_seed_core(orchestrator: AgentOrchestrator):
    """Runs the main loops of the VANTA Seed Core."""
    logger.info("Starting VANTA Seed Core Loops...")
    try:
        # Start the orchestrator's main loops (task processing and breath cycle)
        await orchestrator.start()
    except asyncio.CancelledError:
        logger.info("Main seed core run task cancelled.")
    except Exception as e:
        logger.error(f"Unhandled exception in run_seed_core: {e}", exc_info=True)
    finally:
        logger.info("VANTA Seed Core run loop finishing.")
        # Ensure orchestrator stops gracefully even on error
        await orchestrator.stop()

async def main():
    """Main entry point."""
    logger.info("Starting VANTA Application...")
    
    # Load configurations
    blueprint = load_yaml_config(BLUEPRINT_FILE)
    agent_definitions = load_json_config(AGENT_INDEX_FILE)
    
    if blueprint is None or agent_definitions is None:
        logger.critical("Failed to load essential configuration. Exiting.")
        return

    # Initialize the Unified Orchestrator
    orchestrator = initialize_seed_orchestrator(blueprint, agent_definitions)

    # --- Agent Registration (Now handled INSIDE orchestrator._load_agents) ---
    # No longer need to manually register agents here
    # active_agents = { 
    #     agent_id: details 
    #     for agent_id, details in agent_definitions.items() 
    #     if details.get('status') == 'active'
    # }
    # logger.info(f"Registering {len(active_agents)} active agents for SwarmWeave...")
    # for agent_id in active_agents:
    #     orchestrator.register_agent_for_swarm(agent_id) # Only register for swarm
    # ---------------------------------------------------------------------

    # Run the main Seed Core loops
    main_task = asyncio.create_task(run_seed_core(orchestrator))

    # Handle graceful shutdown (e.g., on Ctrl+C)
    try:
        await main_task
    except asyncio.CancelledError:
        logger.info("Main application task cancelled.")
    finally:
        logger.info("VANTA Application Shutting Down...")
        if not main_task.done():
             main_task.cancel()
             await main_task # Allow cancellation to propagate
        await orchestrator.stop() # Ensure stop is called if not already
        logger.info("VANTA Application Shutdown Complete.")

if __name__ == "__main__":
    asyncio.run(main())

# --- Deprecated run_framework using old orchestrator --- 
# def run_framework(blueprint, agent_definitions):
#    ... (Old implementation commented out or removed) ...

# --- Application Setup (Placeholder for FastAPI or main loop) ---

# Example using FastAPI (requires uncommenting in requirements.txt)
# from fastapi import FastAPI
# app = FastAPI(title="VANTA Framework API")

# @app.get("/")
# async def root():
#     return {"message": "VANTA Framework running...", "blueprint_version": blueprint.get('version', 'N/A')}

# Placeholder for main execution logic if not an API
# --- Updated run_framework to use agent_definitions ---
# def run_framework(blueprint, agent_definitions):
#     print("\n--- Initializing VANTA Framework --- ")
#     # Config values like version/stance should come from blueprint or config.py if defined there
#     print(f"Version: {blueprint.get('version', 'N/A')}") 
#     print(f"Moral Stance: {blueprint.get('moral_stance', 'Not Defined').strip()}")
#     print(f"Router Strategy: {blueprint.get('router_strategy', {})}")
#     print(f"Registered Agents: {list(agent_definitions.keys())}") 

#     # --- Initialize Core Agents ---
#     orchestrator_def = agent_definitions.get('AgentOrchestrator')

#     orchestrator = None
#     # --- Removed direct initialization of MemoryWeaver and RuleSmith ---
#     # memory_weaver = None
#     # rule_smith = None

#     # --- Simplified initialization - Orchestrator handles loading others ---
#     if orchestrator_def:
#         # Pass blueprint and all definitions to Orchestrator
#         orchestrator = AgentOrchestrator(
#             agent_name='AgentOrchestrator', 
#             definition=orchestrator_def,
#             blueprint=blueprint,
#             all_agent_definitions=agent_definitions
#             # Logger is handled internally by AgentOrchestrator now
#         )
#         print("AgentOrchestrator initialized.")
#     else:
#         print("ERROR: AgentOrchestrator definition not found in agent index!")

#     # TODO: Initialize other agents (AutoMutator, PromptSmith etc.) via Orchestrator? YES
#     # TODO: Initialize VANTA.SOLVE kernel
#     # TODO: Initialize supporting agents for VANTA.SOLVE
#     # TODO: Start main loop / listener / task processor / ritual scheduler via Orchestrator
#     if orchestrator:
#         print("\nStarting Orchestrator...")
#         # --- Orchestrator.start() now likely expects an existing loop ---
#         # orchestrator.start() # Start the main process/loop
#         # Instead, return the instance to be run in the main loop
#         return orchestrator 
#     else:
#         print("\nERROR: Orchestrator failed to initialize. Framework cannot run.")
#         return None

#     # print("--------------------------------------")

# --- Main Execution ---

# async def main_async():
#     """Main async entry point to load config and run framework."""
#     # Config loading and logging setup happens when config.py is imported
#     # print("Starting VANTA (async)...") # Already printed in config.py maybe?
#     blueprint = load_blueprint()
# 
#     if blueprint:
#         agent_definitions = load_agent_definitions()
# 
#         if agent_definitions:
#             orchestrator = run_framework(blueprint, agent_definitions)
#             if orchestrator:
#                 # Keep the event loop running until orchestrator stops or is interrupted
#                 print("Framework initialized. Orchestrator starting task loop...")
#                 # Start the processing loop within the main async function
#                 processing_task = asyncio.create_task(orchestrator.run_processing_loop())
#                 # Start the scheduler in the background
#                 # Check if scheduler exists before starting (it might have been commented out)
#                 if hasattr(orchestrator, 'scheduler') and not orchestrator.scheduler.running:
#                     orchestrator.scheduler.start()
#                     # Use orchestrator's logger
#                     orchestrator.logger.info("Background scheduler started from main_async.") 
#                 
#                 # --- Add a simple initial task for testing ---
#                 initial_task_data = {
#                     "intent": "prompt_creation", 
#                     "payload": {"topic": "hello world"},
#                     "task_id": f"init_task_{uuid.uuid4().hex[:6]}", 
#                     "source_agent": "SystemStartup"
#                 }
#                 await orchestrator.add_task(initial_task_data)
#                 # Use orchestrator's logger
#                 orchestrator.logger.info(f"Added initial test task {initial_task_data['task_id']} to queue.") 
#                 # -------------------------------------------
#                 
#                 try:
#                     # Keep running - wait for the processing task or external shutdown
#                     await processing_task 
#                 except KeyboardInterrupt:
#                     print("\nKeyboardInterrupt received. Shutting down...")
#                 finally:
#                     # Graceful shutdown
#                     await orchestrator.stop()
#                     print("Framework shutdown complete.")
#             else:
#                  print("Orchestrator initialization failed.")
#         else:
#             print("Exiting due to missing or invalid agent definitions.")
#     else:
#         print("Exiting due to missing or invalid blueprint.")

# if __name__ == "__main__":
#     # --- Use asyncio.run to manage the event loop ---
#     # config.py is imported first, setting everything up
#     try:
#         asyncio.run(main_async())
#     except KeyboardInterrupt:
#         print("\nShutdown requested by user (Ctrl+C).")
#     # --- Removed old synchronous call ---
#     # print("Starting VANTA...")
#     # blueprint = load_blueprint()
#     # 
#     # if blueprint:
#     #     # --- Load definitions from JSON instead of configs from YAML ---
#     #     agent_definitions = load_agent_definitions()
#     # 
#     #     if agent_definitions: # Proceed only if definitions were loaded
#     #          # Option 1: Run as a background process/loop (example)
#     #         run_framework(blueprint, agent_definitions)
#     # 
#     #         # Option 2: Run as a FastAPI server (example)
#     #         # print("Starting API server...")
#     #         # uvicorn.run(app, host="0.0.0.0", port=8000) # Match port in vanta_router_and_lora.py?
#     #     else:
#     #         print("Exiting due to missing or invalid agent definitions.")
#     # else:
#     #     print("Exiting due to missing or invalid blueprint.") 