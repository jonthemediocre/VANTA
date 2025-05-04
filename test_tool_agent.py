import asyncio
import logging
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
logger = logging.getLogger("test_tool_agent")

# Assume VantaMasterCore can be imported
# Ensure PYTHONPATH is set correctly if running from root
# Add project root to sys.path if necessary:
# import sys
# import os
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from vanta_seed.core.vanta_master_core import VantaMasterCore

async def run_tool_test():
    logger.info("Starting ToolAgent test...")

    # Initialize Vanta Core
    # Ensure config.yaml and blueprint.yaml exist and are configured
    try:
        master_core = VantaMasterCore(config_path='config.yaml', blueprint_path='blueprint.yaml')
        master_core.startup() # Loads config, blueprint, agents
        logger.info(f"Vanta Core started. Loaded agents: {master_core.get_all_agent_states().keys()}")
    except Exception as e:
        logger.error(f"Failed to initialize Vanta Master Core: {e}", exc_info=True)
        return

    # --- Test Case 1: Calculate Tool (Success) ---
    logger.info("--- Test Case 1: Calculate Tool (Success) ---")
    task_data_calc_success = {
        "task_id": str(uuid.uuid4()),
        "intent": "execute_tool",
        "origin_agent": "test_script",
        # "target_agent": "ToolAgent", # Optional: Rely on intent routing
        "data": {
            "tool_name": "calculate",
            "parameters": {
                "operand1": 10,
                "operand2": 5,
                "operation": "add"
            }
        },
        "metadata": {"test_case": 1}
    }

    result1 = await master_core.submit_task(task_data_calc_success)
    logger.info(f"Test Case 1 Result: {result1}")
    assert result1.get('status') == 'success' and result1.get('result', {}).get('result') == 15

    await asyncio.sleep(0.1) # Small delay between tasks

    # --- Test Case 2: Query Tool (Success) ---
    logger.info("--- Test Case 2: Query Tool (Success) ---")
    task_data_query_success = {
        "task_id": str(uuid.uuid4()),
        "intent": "execute_tool",
        "origin_agent": "test_script",
        "data": {
            "tool_name": "query",
            "parameters": {
                "query": "active pilgrims"
            }
        },
        "metadata": {"test_case": 2}
    }

    result2 = await master_core.submit_task(task_data_query_success)
    logger.info(f"Test Case 2 Result: {result2}")
    assert result2.get('status') == 'success' and 'Data found for query' in result2.get('result', {}).get('result', '')

    await asyncio.sleep(0.1)

    # --- Test Case 3: Tool Not Found ---
    logger.info("--- Test Case 3: Tool Not Found ---")
    task_data_tool_not_found = {
        "task_id": str(uuid.uuid4()),
        "intent": "execute_tool",
        "origin_agent": "test_script",
        "data": {
            "tool_name": "non_existent_tool",
            "parameters": {}
        },
        "metadata": {"test_case": 3}
    }

    result3 = await master_core.submit_task(task_data_tool_not_found)
    logger.info(f"Test Case 3 Result: {result3}")
    assert result3.get('status') == 'error' and 'not available' in result3.get('error', '')

    await asyncio.sleep(0.1)

    # --- Test Case 4: Missing Parameter ---
    logger.info("--- Test Case 4: Missing Parameter ---")
    task_data_missing_param = {
        "task_id": str(uuid.uuid4()),
        "intent": "execute_tool",
        "origin_agent": "test_script",
        "data": {
            "tool_name": "calculate",
            "parameters": {
                "operand1": 10
                # Missing operand2
            }
        },
        "metadata": {"test_case": 4}
    }

    result4 = await master_core.submit_task(task_data_missing_param)
    logger.info(f"Test Case 4 Result: {result4}")
    assert result4.get('status') == 'success' # Tool itself returns error in result field
    assert 'Missing \'operand2\' parameter' in result4.get('result', {}).get('error', '')


    # --- Test Case 5: Invalid Parameters Type ---
    logger.info("--- Test Case 5: Invalid Parameters Type ---")
    task_data_invalid_params = {
        "task_id": str(uuid.uuid4()),
        "intent": "execute_tool",
        "origin_agent": "test_script",
        "data": {
            "tool_name": "calculate",
            "parameters": "not_a_dictionary" # Invalid type
        },
        "metadata": {"test_case": 5}
    }

    result5 = await master_core.submit_task(task_data_invalid_params)
    logger.info(f"Test Case 5 Result: {result5}")
    # This error is now caught within ToolAgent.execute
    assert result5.get('status') == 'error' and 'parameters must be a dictionary' in result5.get('error', '')


    # Shutdown
    master_core.shutdown()
    logger.info("ToolAgent test finished.")

if __name__ == "__main__":
    asyncio.run(run_tool_test()) 