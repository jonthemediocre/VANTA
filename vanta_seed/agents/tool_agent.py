import asyncio
from typing import Dict, Any, Optional, List
import logging
import json
import uuid

from .base_agent import BaseAgent
from .agent_utils import PilgrimCommunicatorMixin, MCPToolingMixin
from vanta_seed.core.models import AgentConfig, TaskData
from vanta_seed.core.data_models import AgentMessage

logger = logging.getLogger(__name__)

# --- Mock Tool Implementations (Replace with actual tool logic/registry) ---
def mock_query_tool(params: Dict[str, Any]) -> Dict[str, Any]:
    query = params.get("query", "")
    if not query:
        return {"error": "Missing 'query' parameter"}
    # Simulate a query result
    return {"result": f"Data found for query: '{query}'", "source": "mock_db"}

def mock_calculate_tool(params: Dict[str, Any]) -> Dict[str, Any]:
    operand1 = params.get("operand1")
    operand2 = params.get("operand2")
    operation = params.get("operation", "add")

    if operand1 is None or operand2 is None:
        return {"error": "Missing 'operand1' or 'operand2' parameter"}

    try:
        op1 = float(operand1)
        op2 = float(operand2)
        if operation == "add":
            result = op1 + op2
        elif operation == "subtract":
            result = op1 - op2
        elif operation == "multiply":
            result = op1 * op2
        elif operation == "divide":
            if op2 == 0:
                return {"error": "Division by zero"}
            result = op1 / op2
        else:
            return {"error": f"Unknown operation: {operation}"}
        return {"result": result}
    except ValueError:
        return {"error": "Invalid numeric operands"}

MOCK_TOOL_REGISTRY = {
    "query": mock_query_tool,
    "calculate": mock_calculate_tool
}
# --------------------------------------------------------------------------

class ToolAgent(BaseAgent, PilgrimCommunicatorMixin, MCPToolingMixin):
    """
    An agent specializing in using MCP (Multi-Capability Platform) tools.
    Inherits communication and base tool handling.
    """
    def __init__(self, name: str, config: AgentConfig, logger: logging.Logger, orchestrator_ref: Optional[Any] = None):
        """
        Initializes the ToolAgent.
        Uses BaseAgent init, then MCPToolingMixin init.
        """
        # Call BaseAgent init first, including orchestrator_ref
        super().__init__(name=name, config=config, logger=logger, orchestrator_ref=orchestrator_ref)

        # Initialize MCPToolingMixin specific parts (if any needed beyond BaseAgent)
        # MCPToolingMixin.__init__(self) # Assuming it doesn't need explicit init args separate from BaseAgent

        # Access settings via self.config
        # Use direct attribute access for Pydantic models, provide default if attribute might be missing
        self.allowed_tools = getattr(self.config.settings, 'allowed_tools', ['query', 'calculate']) # Example setting

        self.logger.info(f"ToolAgent '{self.name}' initialized. Allowed tools: {self.allowed_tools}")

    async def execute(self, task: TaskData) -> Dict[str, Any]:
        """Executes a tool based on the task data."""
        self.logger.info(f"ToolAgent '{self.name}' executing task: {task.task_id} (Intent: {task.intent})")

        if task.intent != "execute_tool":
            self.logger.warning(f"Received task with incorrect intent '{task.intent}'. Expected 'execute_tool'.")
            return {"error": f"Invalid intent for ToolAgent: {task.intent}", "task_id": task.task_id}

        # --- Extract tool details from TaskData --- #
        tool_name = task.data.get("tool_name")
        parameters = task.data.get("parameters")

        if not tool_name:
            self.logger.error(f"Task {task.task_id} is missing 'tool_name' in data.")
            return {"error": "Missing 'tool_name' in task data", "task_id": task.task_id}

        if not isinstance(parameters, dict):
            self.logger.error(f"Task {task.task_id} 'parameters' must be a dictionary, got {type(parameters)}.")
            # Allow empty params, default to empty dict
            parameters = {} if parameters is None else { "error": "parameters must be a dictionary" }
            if "error" in parameters:
                 return {**parameters, "task_id": task.task_id}

        self.logger.debug(f"Attempting to execute tool '{tool_name}' with params: {parameters}")

        # --- Find and execute the tool --- #
        tool_function = self.tool_registry.get(tool_name)

        if not tool_function or not callable(tool_function):
            self.logger.error(f"Tool '{tool_name}' not found or is not callable in the registry.")
            return {"error": f"Tool '{tool_name}' not available", "task_id": task.task_id}

        try:
            # Assuming tool functions are synchronous for now
            # If tools can be async, use `await tool_function(parameters)`
            tool_result = tool_function(parameters)
            self.logger.info(f"Tool '{tool_name}' executed successfully.")
            # Return the direct result from the tool function
            return {
                "status": "success",
                "tool_name": tool_name,
                "result": tool_result,
                "task_id": task.task_id
            }
        except Exception as e:
            self.logger.error(f"Error executing tool '{tool_name}': {e}", exc_info=True)
            return {
                "status": "error",
                "tool_name": tool_name,
                "error": f"Exception during tool execution: {str(e)}",
                "task_id": task.task_id
            }

    async def startup(self):
        """Announces the agent's identity upon startup."""
        logger.info(f"[Pilgrim Awakens] -> {self.name}: I am {self.symbolic_identity.get('archetype')} -> {self.symbolic_identity.get('mythos_role')}")
        # No super().startup()

    async def perform_task(self, task_data: Dict[str, Any], current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handles executing tool calls or identity requests (required by BaseAgent).
        REVERTED: Expects nested parameters dict in payload.
        """
        task_result = {}
        intent = task_data.get("intent")
        payload = task_data.get("payload", {})

        try:
            if intent == "execute_tool":
                # Expect nested structure now
                tool_name = payload.get("tool_name")
                tool_parameters = payload.get("parameters", {}) # Expect nested dict

                if not tool_name:
                     return {"error": "Missing tool_name in payload."} 
                if not isinstance(tool_parameters, dict):
                     return {"error": "Tool parameters must be a dictionary."}

                # Check if tool is allowed
                if tool_name in self.allowed_tools:
                    logger.info(f"ToolAgent '{self.name}' executing allowed tool: '{tool_name}' with params: {tool_parameters}")
                    # Generate a unique ID for this specific tool call
                    tool_call_id = f"tool_{uuid.uuid4().hex[:8]}"
                    # --- Live Handling for Basic Tools --- 
                    tool_result = await self.handle_tool_call(tool_name, tool_parameters, tool_call_id)
                    # tool_result should now be the ToolResponse-like dict
                    task_result = {"status": "success", "tool_output": tool_result}
                    # ---------------------------------- #
                else:
                    logger.warning(f"ToolAgent '{self.name}' received request for unsupported/disallowed tool: '{tool_name}'")
                    task_result = {"status": "error", "error": f"Unsupported or disallowed tool: {tool_name}"}
            
            elif intent == "identity":
                 # Use the structure from BaseAgent if available
                 archetype = self.symbolic_identity.archetype if hasattr(self.symbolic_identity, 'archetype') else 'UnknownArchetype'
                 mythos_role = self.symbolic_identity.mythos_role if hasattr(self.symbolic_identity, 'mythos_role') else 'UnknownRole'
                 identity_str = f"I am {archetype} -> {mythos_role}."
                 # Return just the string for identity task
                 task_result = {"status": "success", "output": identity_str, "summary": "Returned symbolic identity."}
                 
            else:
                logger.warning(f"ToolAgent '{self.name}' received unknown intent for perform_task: '{intent}'")
                task_result = {"status": "error", "error": f"Unknown intent: {intent}", "summary": "Unknown intent received."}
        
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"ToolAgent '{self.name}' error during perform_task: {e}", exc_info=True)
            task_result = {"status": "error", "error": f"Internal error: {error_type}", "summary": "Agent execution failed."}
            
        # Base class expects dict containing task_result, new_state_data, trail_signature_data
        return {"task_result": task_result, "new_state_data": {}, "trail_signature_data": None}

    # Internal tool handler (used by perform_task)
    async def handle_tool_call(self, tool_name: str, tool_arguments: Dict[str, Any], tool_call_id: str) -> Dict[str, Any]:
        """
        Executes a specific tool call and returns a result formatted like ToolResponse.
        REVERTED: Expects arguments in the tool_arguments dictionary.
        Args:
            tool_name (str): The name of the tool function to call.
            tool_arguments (Dict[str, Any]): The arguments for the tool (nested parameters).
            tool_call_id (str): The unique ID for this tool call request.

        Returns:
            Dict[str, Any]: A dictionary mimicking the ToolResponse structure.
        """
        response_content = {}
        status: Literal['success', 'error'] = 'error' # Default to error
        error_message: Optional[str] = None
        
        # --- Live Handling Implementation --- #
        logger.debug(f"Handling tool call '{tool_call_id}' for tool '{tool_name}' with args: {tool_arguments}")
        try:
            if tool_name == "query":
                # Expect nested tool_arguments['term']
                query_term = str(tool_arguments.get('term', ''))
                if not query_term:
                     raise ValueError("Missing 'term' argument for query tool.")
                logger.debug(f"Simulating query for: {query_term}")
                if "status" in query_term.lower():
                    response_content = {"results": ["System OK", "Agent EchoAgent Active"]}
                else:
                    response_content = {"results": [f"Data related to '{query_term}'"]}
                status = 'success'
                
            elif tool_name == "calculate":
                # Expect nested tool_arguments['expression']
                expr = str(tool_arguments.get('expression', ''))
                if not expr:
                    raise ValueError("Missing 'expression' argument for calculate tool.")
                logger.debug(f"Simulating calculation for: {expr}")
                # Basic eval for simplicity - CAUTION in production
                calc_result = eval(expr, {"__builtins__": {}}, {}) 
                response_content = {"result": calc_result}
                status = 'success'
                     
            elif tool_name == "fetch":
                 # Expect nested tool_arguments['url']
                 url = str(tool_arguments.get('url', ''))
                 if not url:
                      raise ValueError("Missing 'url' argument for fetch tool.")
                 logger.debug(f"Simulating fetch for: {url}")
                 if "example.com" in url:
                     response_content = {"status_code": 200, "content": "<html>Example Content</html>"}
                 else:
                      response_content = {"status_code": 404, "error": "URL not found"} # Tool itself reports error in content
                 status = 'success' # The fetch tool executed successfully, even if URL not found
                 
            else:
                error_message = f"Tool '{tool_name}' live handling not implemented."
                status = 'error'
                logger.warning(error_message)
        
        except Exception as e:
             error_type = type(e).__name__
             error_msg = str(e)
             logger.error(f"Error executing tool '{tool_name}' (Call ID: {tool_call_id}): {error_type} - {error_msg}", exc_info=True)
             error_message = f"Execution failed: {error_type} - {error_msg}"
             status = 'error'
             response_content = {"error_details": error_message}

        # --- Format output like ToolResponse --- 
        tool_response = {
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": json.dumps(response_content), # Serialize content to JSON string
            "status": status,
            "error_message": error_message
        }
        # ---------------------------------------
        return tool_response

    async def receive_message(self, message: AgentMessage): # <<< RENAMED CORRECTLY
        """Handles direct messages (required by BaseAgent)."""
        sender = message.sender_id or "UnknownSender"
        logger.info(f"ToolAgent '{self.name}' received message from '{sender}'. Type: {message.intent}")
        pass

    async def shutdown(self):
        logger.info(f"ToolAgent '{self.name}' shutting down.")
        # No super().shutdown()
 