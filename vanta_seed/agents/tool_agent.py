import asyncio
from typing import Dict, Any, Optional, List
import logging

from .base_agent import BaseAgent
from .agent_utils import PilgrimCommunicatorMixin, MCPToolingMixin
from vanta_seed.core.data_models import AgentMessage # Needed for receive_message signature

logger = logging.getLogger(__name__)

class ToolAgent(BaseAgent, PilgrimCommunicatorMixin, MCPToolingMixin):
    """
    Agent responsible for interacting with external tools or APIs (MCP).
    (Minimal viable implementation with basic live tool handling)
    """
    def __init__(self, name: str, initial_state: Dict[str, Any], settings: Optional[Dict[str, Any]] = None):
        """
        Initializes the ToolAgent based on Crown specification.
        """
        super().__init__(name=name, initial_state=initial_state)
        
        # --- Load settings FROM self.state --- 
        current_state = self.current_state
        agent_settings = current_state.get("settings", {})
        self.symbolic_identity = current_state.get("symbolic_identity", {
            "archetype": "Bridge",
            "mythos_role": "Instrument of Will"
        })
        self.awareness_mode = agent_settings.get('awareness_mode', 'basic')
        self.supported_tools = agent_settings.get('supported_tools', [])
        
        # We don't currently use settings in ToolAgent, but accept it for compatibility
        self.agent_settings = settings if settings is not None else {}
        # Example: Load available tools from settings
        self.execution_mode = self.agent_settings.get('execution_mode', 'basic')
        self.available_tools = self.agent_settings.get('available_tools', ['query', 'calculate', 'fetch']) 
        
        logger.info(f"ToolAgent '{self.name}' initialized via BaseAgent state. Mode: {self.execution_mode}, Tools: {self.available_tools}")

    # <<< ADD Concrete execute method to satisfy ABC check >>>
    async def execute(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Overrides the abstract execute method.
        Delegates execution logic to the base class's implementation.
        """
        self.logger.debug(f"Agent '{self.name}' delegating execute to BaseAgent.")
        if hasattr(super(), 'execute') and callable(super().execute):
             return await super().execute(task_data)
        else:
             self.logger.error(f"BaseAgent does not have a callable execute method for agent '{self.name}'!")
             # Basic fallback
             try:
                 current_state_dict = self.current_state
                 task_result = await self.perform_task(task_data, current_state_dict)
                 return {"task_result": task_result, "new_state_data": {}, "trail_signature_data": None}
             except Exception as e:
                 self.logger.exception(f"Error in fallback execute for '{self.name}'")
                 return {"task_result": {"error": str(e)}, "new_state_data": {}, "trail_signature_data": None}
    # <<< END ADDED execute method >>>

    async def startup(self):
        """Announces the agent's identity upon startup."""
        logger.info(f"[Pilgrim Awakens] -> {self.name}: I am {self.symbolic_identity.get('archetype')} -> {self.symbolic_identity.get('mythos_role')}")
        # No super().startup()

    async def perform_task(self, task_data: Dict[str, Any], current_state: Dict[str, Any]) -> Dict[str, Any]: # <<< Kept from previous edit
        """
        Handles executing tool calls or identity requests (required by BaseAgent).
        """
        task_result = {}
        intent = task_data.get("intent")
        payload = task_data.get("payload", {})

        try:
            if intent == "execute_tool":
                tool_name = payload.get("tool_name")
                tool_input = payload.get("input")
                
                if tool_name in self.supported_tools:
                    logger.info(f"ToolAgent '{self.name}' executing tool: '{tool_name}'")
                    # --- Live Handling for Basic Tools --- 
                    tool_result = await self.handle_tool_call(tool_name, tool_input)
                    task_result = {"status": "success", "tool_output": tool_result}
                    # ---------------------------------- #
                else:
                    logger.warning(f"ToolAgent '{self.name}' received request for unsupported tool: '{tool_name}'")
                    task_result = {"error": f"Unsupported tool: {tool_name}"}
            
            elif intent == "identity":
                 identity_str = f"I am {self.symbolic_identity.get('archetype')} -> {self.symbolic_identity.get('mythos_role')}."
                 task_result = {"task_result": identity_str}
                 
            else:
                logger.warning(f"ToolAgent '{self.name}' received unknown task type: '{intent}'")
                task_result = {"error": f"Unknown task type: {intent}"}
        
        except Exception as e:
            logger.error(f"ToolAgent '{self.name}' error during perform_task: {e}", exc_info=True)
            task_result = {"error": str(e)}
            
        return task_result # Return only core result

    # Internal tool handler (used by perform_task)
    async def handle_tool_call(self, tool_name: str, tool_input: Any) -> Any:
        """Placeholder for actually executing a tool call."""
        # --- Live Handling Implementation (kept from previous edit) --- #
        if tool_name == "query":
            query_term = str(tool_input.get('term', '')) if isinstance(tool_input, dict) else str(tool_input)
            logger.debug(f"Simulating query for: {query_term}")
            if "status" in query_term.lower():
                return {"results": ["System OK", "Agent EchoAgent Active"]}
            return {"results": [f"Data related to '{query_term}'"]}
            
        elif tool_name == "calculate":
            expr = str(tool_input.get('expression', '')) if isinstance(tool_input, dict) else str(tool_input)
            logger.debug(f"Simulating calculation for: {expr}")
            try:
                result = eval(expr, {"__builtins__": {}}, {}) 
                return {"result": result}
            except Exception as e:
                 logger.error(f"Calculation failed for '{expr}': {e}")
                 return {"error": f"Calculation failed: {e}"}
                 
        elif tool_name == "fetch":
             url = str(tool_input.get('url', '')) if isinstance(tool_input, dict) else str(tool_input)
             logger.debug(f"Simulating fetch for: {url}")
             if "example.com" in url:
                 return {"status_code": 200, "content": "<html>Example Content</html>"}
             return {"status_code": 404, "error": "URL not found"}
             
        else:
            return {"error": f"Tool '{tool_name}' live handling not implemented."}
        # ---------------------------------- #

    async def receive_message(self, message: AgentMessage): # <<< RENAMED CORRECTLY
        """Handles direct messages (required by BaseAgent)."""
        sender = message.sender_id or "UnknownSender"
        logger.info(f"ToolAgent '{self.name}' received message from '{sender}'. Type: {message.intent}")
        pass

    async def shutdown(self):
        logger.info(f"ToolAgent '{self.name}' shutting down.")
        # No super().shutdown()
 