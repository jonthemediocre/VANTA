"""
Basic CLI interface for interacting with the VANTA Agent Orchestrator.
"""
import argparse
import asyncio
import logging
import sys
import os
import json

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
    from orchestrator import AgentOrchestrator, TaskData
    from utils import load_agent_definitions # Import the new function
except ImportError as e:
    print(f"Error importing necessary modules: {e}", file=sys.stderr)
    print("Please ensure orchestrator.py and utils.py exist and are importable.", file=sys.stderr)
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger("VANTA_CLI")

def parse_arguments():
    parser = argparse.ArgumentParser(description="VANTA OS Command Line Interface")
    parser.add_argument("--intent", required=True, help="The primary intent for the task.")
    parser.add_argument("--prompt", help="Optional text prompt for the task payload.")
    parser.add_argument("--payload", help="Optional JSON string for the task payload.")
    # Add more arguments as needed for different intents/payloads
    return parser.parse_args()

async def main():
    args = parse_arguments()
    logger.info(f"CLI invoked with intent: {args.intent}")

    try:
        # --- Load Agent Definitions --- 
        logger.info("Loading agent definitions...")
        all_agent_definitions = load_agent_definitions() # Load all definitions
        
        # --- Get Orchestrator Definition --- 
        orchestrator_name = "AgentOrchestrator"
        orchestrator_def = all_agent_definitions.get(orchestrator_name)
        if not orchestrator_def:
            logger.error(f"Definition for '{orchestrator_name}' not found in agents.index.mpc.json.")
            return
            
        # --- Instantiate Orchestrator Directly --- 
        logger.info(f"Instantiating {orchestrator_name}...")
        # Assuming blueprint/other args might be needed - using None for now
        orchestrator_instance = AgentOrchestrator(
            agent_name=orchestrator_name,
            definition=orchestrator_def,
            blueprint={},
            all_agent_definitions=all_agent_definitions
        )
        logger.info(f"{orchestrator_name} instantiated.")
        # -------------------------------------------

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

        # Prepare task data (assuming TaskData model exists and works)
        task_dict = {
            "intent": args.intent,
            "payload": payload_data,
            "context": {"source": "cli"} # Add some context
            # TaskData model might add timestamp, id, etc.
        }
        
        # Validate with Pydantic if needed, otherwise just use the dict
        # task = TaskData(**task_dict) 
        # task_to_submit = task.dict()
        task_to_submit = task_dict # Use the dict directly if TaskData is just for API

        logger.info(f"Submitting task to orchestrator: {task_to_submit}")
        # Start the orchestrator's processing loop in the background
        processing_task = asyncio.create_task(orchestrator_instance.run_processing_loop())
        
        # Add the task to the queue
        await orchestrator_instance.add_task(task_to_submit)
        
        # Give the orchestrator some time to process (crude way, better ways exist)
        logger.info("Waiting for task processing... (15s)")
        await asyncio.sleep(15) # Wait 15 seconds for processing

        logger.info("CLI task submitted. Check orchestrator logs for results.")
        # Optionally, add logic here to retrieve and display the result if possible
        
        await orchestrator_instance.stop() # Attempt graceful shutdown
        processing_task.cancel() # Cancel the loop
        try:
            await processing_task # Allow cancellation to propagate
        except asyncio.CancelledError:
             logger.info("Orchestrator loop cancelled.")

    except FileNotFoundError as e:
        logger.error(f"Configuration file error: {e}")
    except ValueError as e:
        logger.error(f"Configuration parsing error: {e}")
    except Exception as e:
        logger.error(f"An error occurred during CLI execution: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main()) 