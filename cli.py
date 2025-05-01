"""
Basic CLI interface for interacting with the VANTA Agent Orchestrator.
"""
import argparse
import asyncio
import logging
import sys
import os
import json
import yaml # Added for config loading
from pathlib import Path # Added for path handling

# --- Add dotenv loading --- 
from dotenv import load_dotenv
load_dotenv() # This loads variables from .env into the environment
# ------------------------

# Make sure vanta_seed package is discoverable
# Adjust the path if your script structure is different
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = current_dir # Assuming cli.py is in the project root
# sys.path.insert(0, project_root) # No longer needed if imports relative to root work

# Now import orchestrator and other necessary modules
try:
    # Assuming orchestrator is now VantaMasterCore
    from vanta_seed.core.vanta_master_core import VantaMasterCore 
    # Import config loading utilities if they exist, or define here
    # from config import get_blueprint_path, get_agent_index_path # Ideal
except ImportError as e:
    print(f"Error importing necessary modules: {e}", file=sys.stderr)
    print("Please ensure vanta_seed paths are correct and dependencies installed.", file=sys.stderr)
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger("VANTA_CLI")

# --- Helper Functions for Commands ---

def check_config_files():
    """Checks if essential configuration files exist and are loadable."""
    logger.info("Running Configuration Checks...")
    # Use paths from environment or defaults, similar to config.py
    base_dir = Path(project_root) # Assuming cli.py is in root
    blueprint_path = base_dir / os.getenv("VANTA_BLUEPRINT_FILE", "blueprint.yaml")
    agent_index_path = base_dir / os.getenv("VANTA_AGENT_INDEX_FILE", "agents.index.mpc.json")
    
    errors = False

    # Check blueprint
    if not blueprint_path.exists():
        logger.error(f"Blueprint file not found: {blueprint_path}")
        errors = True
    else:
        try:
            with open(blueprint_path, 'r') as f:
                yaml.safe_load(f)
            logger.info(f"Blueprint file OK: {blueprint_path}")
        except Exception as e:
            logger.error(f"Error loading Blueprint file {blueprint_path}: {e}")
            errors = True

    # Check agent index
    if not agent_index_path.exists():
        logger.error(f"Agent index file not found: {agent_index_path}")
        errors = True
    else:
        try:
            with open(agent_index_path, 'r') as f:
                json.load(f)
            logger.info(f"Agent index file OK: {agent_index_path}")
        except Exception as e:
            logger.error(f"Error loading Agent index file {agent_index_path}: {e}")
            errors = True
            
    if errors:
        logger.error("Configuration Check Failed.")
        return False
    else:
        logger.info("Configuration Check Passed.")
        return True

async def run_health_checks():
    """Runs health checks on the system (placeholder)."""
    logger.info("Running Health Checks...")
    # Placeholder: Add real checks later (e.g., DB connection, agent ping)
    await asyncio.sleep(0.1) # Simulate work
    logger.info("Health Checks Passed (Placeholder.)")
    return True

# --- Argument Parsing ---

def parse_arguments():
    parser = argparse.ArgumentParser(description="VANTA OS Command Line Interface")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Subparser for submitting a task
    parser_submit = subparsers.add_parser("submit", help="Submit a task to the orchestrator")
    parser_submit.add_argument("--intent", required=True, help="The primary intent for the task.")
    parser_submit.add_argument("--prompt", help="Optional text prompt for the task payload.")
    parser_submit.add_argument("--payload", help="Optional JSON string for the task payload.")

    # Subparser for checking config
    parser_check_config = subparsers.add_parser("check-config", help="Check configuration files")
    
    # Subparser for health checks
    parser_health = subparsers.add_parser("run-health-checks", help="Run system health checks")

    # Add more subparsers for other commands

    return parser.parse_args()

# --- Main Execution Logic ---

async def main():
    args = parse_arguments()

    if args.command == "submit":
        logger.info(f"CLI invoked with command: submit, intent: {args.intent}")
        # --- Task Submission Logic (Simplified - Needs VantaMasterCore setup) ---
        logger.warning("Task submission via CLI is currently simplified and may need VantaMasterCore setup.")
        # Construct payload
        payload_data = {}
        if args.prompt:
            payload_data['prompt'] = args.prompt
        elif args.payload:
            try:
                payload_data = json.loads(args.payload)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON provided for payload: {args.payload}")
                return

        task_to_submit = {
            "intent": args.intent,
            "payload": payload_data,
            "context": {"source": "cli"}
        }
        logger.info(f"Task prepared (would be submitted to orchestrator): {task_to_submit}")
        # TODO: Integrate properly with VantaMasterCore for actual submission
        # Example:
        # orchestrator = setup_orchestrator() # Needs a function to init orchestrator
        # await orchestrator.add_task(task_to_submit)
        # await orchestrator.run_once() # Or similar method if not running full loop

    elif args.command == "check-config":
        logger.info("CLI invoked with command: check-config")
        if not check_config_files():
            sys.exit(1) # Exit with error code if checks fail

    elif args.command == "run-health-checks":
        logger.info("CLI invoked with command: run-health-checks")
        if not await run_health_checks():
            sys.exit(1) # Exit with error code if checks fail
            
    else:
        logger.error(f"Unknown command: {args.command}")
        # parser.print_help() # Removed to avoid circular import if parser is needed elsewhere
        print("Available commands: submit, check-config, run-health-checks")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 