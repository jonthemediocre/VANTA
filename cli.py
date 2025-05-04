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
import requests # Added for HTTP requests

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
    parser_submit.add_argument("--payload-file", help="Optional path to a JSON file containing the task payload.")
    parser_submit.add_argument("--agent", help="Optional name of the specific agent to target.")

    # Subparser for checking config
    parser_check_config = subparsers.add_parser("check-config", help="Check configuration files")
    
    # Subparser for health checks
    parser_health = subparsers.add_parser("run-health-checks", help="Run system health checks")

    # Add more subparsers for other commands

    return parser.parse_args()

# --- Main Execution Logic ---

async def main():
    # Explicitly load .env here for CLI script context
    dotenv_path = Path('.') / '.env' 
    logger.info(f"Attempting to load environment variables from: {dotenv_path.resolve()}")
    loaded = load_dotenv(dotenv_path=dotenv_path, override=True, verbose=True) 
    logger.info(f"dotenv loaded: {loaded}")
    if not loaded:
        logger.warning("Failed to load .env file using explicit path.")
        
    # --- Read API Key immediately after loading --- 
    cli_api_key = os.getenv("VANTA_API_KEY")
    if cli_api_key:
        logger.info("VANTA_API_KEY found immediately after load_dotenv.")
    else:
        logger.warning("VANTA_API_KEY NOT found immediately after load_dotenv.")
    # ------------------------------------------
        
    args = parse_arguments()

    if args.command == "submit":
        logger.info(f"CLI invoked with command: submit, intent: {args.intent}")
        
        # --- Task Submission Logic (Using HTTP Request) ---
        # Construct payload - Prioritize file, then payload string, then prompt
        payload_data = {}
        if args.payload_file:
            try:
                with open(args.payload_file, 'r') as f:
                    payload_data = json.load(f)
                logger.info(f"Loaded payload from file: {args.payload_file}")
            except FileNotFoundError:
                logger.error(f"Payload file not found: {args.payload_file}")
                return
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in payload file: {args.payload_file}")
                return
            except Exception as e:
                 logger.error(f"Error reading payload file {args.payload_file}: {e}")
                 return
        elif args.payload: # Only use if file not given
            try:
                payload_data = json.loads(args.payload)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON provided for payload string: {args.payload}")
                return
        elif args.prompt: # Only use if file and payload string not given
            payload_data = {"prompt": args.prompt} 
        else:
             pass # Empty payload if none provided

        # Prepare the full task dictionary for the TaskInput model
        task_to_submit = {
            "intent": args.intent,
            "payload": payload_data,
            "context": {"source": "cli"}, 
            "target_agent": args.agent # <<< UPDATED to use args.agent
        }
        # Remove null target_agent if not provided
        if not task_to_submit["target_agent"]:
            del task_to_submit["target_agent"]
        
        server_url = os.getenv("VANTA_API_URL", "http://127.0.0.1:18888") # <<< Changed default port to 18888 
        submit_endpoint = f"{server_url}/submit_task"
        logger.info(f"Submitting task to: {submit_endpoint}")
        
        # --- Use the API Key read earlier --- 
        # api_key = os.getenv("VANTA_API_KEY") # Don't read again here
        headers = {}
        if cli_api_key: # Use the variable read earlier
            headers["Authorization"] = f"Bearer {cli_api_key}"
            logger.info("Authorization header added using cli_api_key.")
        else:
            logger.warning("cli_api_key variable is empty. Sending request without Authorization header.")
        # -----------------------------------
            
        try:
            response = requests.post(
                submit_endpoint, 
                json=task_to_submit, 
                headers=headers, # <<< Add headers to request
                timeout=30
            )
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            
            # Print the JSON response from the server
            try:
                response_json = response.json()
                print(json.dumps(response_json, indent=2))
            except json.JSONDecodeError:
                logger.error("Failed to decode JSON response from server.")
                print("Raw Response Text:", response.text)

        except requests.exceptions.ConnectionError:
            logger.error(f"Connection Error: Could not connect to the VANTA server at {submit_endpoint}. Is it running?")
            sys.exit(1)
        except requests.exceptions.Timeout:
            logger.error(f"Request timed out connecting to {submit_endpoint}.")
            sys.exit(1)
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred during the request to {submit_endpoint}: {e}")
            # Print response content if available, even on error
            if e.response is not None:
                print("Server Response Status Code:", e.response.status_code)
                print("Server Response Text:", e.response.text)
            sys.exit(1)
        # --------------------------

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