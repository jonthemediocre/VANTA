from typing import Dict, Any, List

# <<< ADDED PurposePulse Class >>>
class PurposePulse:
    """Represents the symbolic resonance state of a Pilgrim."""
    STATES = ["Dormant", "Awake", "Resonant", "Prime"]

    def __init__(self, initial_state: str = "Dormant"):
        if initial_state not in self.STATES:
            raise ValueError(f"Invalid initial_state: {initial_state}. Must be one of {self.STATES}")
        self.state = initial_state

    def escalate(self):
        """Escalates the pulse state to the next level if possible."""
        try:
            index = self.STATES.index(self.state)
            if index < len(self.STATES) - 1:
                self.state = self.STATES[index + 1]
        except ValueError:
            # Should not happen if state is managed correctly
            self.state = "Awake" # Default recovery state

    def deescalate(self):
        """De-escalates the pulse state to the previous level if possible."""
        try:
            index = self.STATES.index(self.state)
            if index > 0:
                self.state = self.STATES[index - 1]
        except ValueError:
            self.state = "Dormant" # Default recovery state
            
    def set_state(self, new_state: str):
        """Directly sets the pulse state if valid."""
        if new_state not in self.STATES:
             raise ValueError(f"Invalid state: {new_state}. Must be one of {self.STATES}")
        self.state = new_state
        
    def get_state(self) -> str:
        """Returns the current pulse state."""
        return self.state
        
    def to_dict(self) -> Dict[str, str]:
        """Returns a dictionary representation."""
        return {"state": self.state}

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'PurposePulse':
        """Creates an instance from a dictionary representation."""
        return cls(initial_state=data.get("state", "Dormant"))
# <<< END PurposePulse Class >>>

# <<< ADDED MythicRole Class >>>
class MythicRole:
    """Manages the layered Mythic Role of a Pilgrim."""
    ROLES = ["Pilgrim", "Herald", "Sage", "Architect"]

    def __init__(self, initial_role: str = "Pilgrim"):
        if initial_role not in self.ROLES:
            raise ValueError(f"Invalid initial role: {initial_role}. Must be one of {self.ROLES}")
        self.current_role = initial_role

    def escalate_role(self):
        """Escalates the role to the next level if possible."""
        try:
            index = self.ROLES.index(self.current_role)
            if index < len(self.ROLES) - 1:
                self.current_role = self.ROLES[index + 1]
        except ValueError:
            self.current_role = "Pilgrim" # Default recovery role

    def deescalate_role(self):
        """De-escalates the role to the previous level if possible."""
        try:
            index = self.ROLES.index(self.current_role)
            if index > 0:
                self.current_role = self.ROLES[index - 1]
        except ValueError:
            self.current_role = "Pilgrim" # Default recovery role
            
    def set_role(self, new_role: str):
        """Directly sets the role if valid."""
        if new_role not in self.ROLES:
             raise ValueError(f"Invalid role: {new_role}. Must be one of {self.ROLES}")
        self.current_role = new_role
        
    def get_role(self) -> str:
        """Returns the current role."""
        return self.current_role
        
    def to_dict(self) -> Dict[str, str]:
        """Returns a dictionary representation."""
        return {"current_role": self.current_role}

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'MythicRole':
        """Creates an instance from a dictionary representation."""
        return cls(initial_role=data.get("current_role", "Pilgrim"))
# <<< END MythicRole Class >>>

class PilgrimCommunicatorMixin:
    """Gives Pilgrims ability to message other Pilgrims via Crown."""
    
    @property
    def orchestrator(self):
        # Attempt to access the orchestrator instance stored on the agent
        return getattr(self, '_orchestrator', None)

    # It's unusual to have a setter without a clear use case immediately,
    # but keeping it as VantaMasterCore assigns itself during agent init.
    @orchestrator.setter
    def orchestrator(self, value):
        # Store the orchestrator reference when VantaMasterCore assigns it
        self._orchestrator = value
        
    @property
    def name(self):
        # Assumes the agent instance has a 'name' attribute
        return getattr(self, 'name', 'UnknownPilgrim')

    async def send_to_pilgrim(self, target_agent_name: str, message: dict):
        """Sends a direct message to another pilgrim via the orchestrator."""
        if not self.orchestrator:
            # Log an error or raise an exception if the orchestrator isn't set
            # logger.error(f"Pilgrim '{self.name}' cannot send message: Orchestrator not set.")
            raise RuntimeError(f"Orchestrator not set for Pilgrim '{self.name}'")
        # Include self.name as the sender automatically
        return await self.orchestrator.send_direct_message(target_agent_name, message, sender_agent=self.name)

class MCPToolingMixin:
    """Enables Pilgrims to emit and handle ToolCalls."""

    # Placeholder for actual tool handling logic within an agent
    async def handle_tool_call(self, tool_call: dict) -> dict:
        # logger.warning(f"Pilgrim '{self.name}' received tool call but handle_tool_call is not implemented.")
        # Default response indicating it's not implemented
        return {"status": "error", "error_message": f"Tool call handling not implemented by {self.name}"}

    # Method to send a tool call request to another agent (likely the ToolAgent)
    async def emit_tool_call(self, target_agent_name: str, tool_call: dict):
        # Check if the agent has the send_to_pilgrim method from the other mixin
        if not hasattr(self, 'send_to_pilgrim'):
             raise AttributeError(f"Pilgrim '{self.name}' needs PilgrimCommunicatorMixin to emit tool calls.")
        # Wrap the tool call in a standard message format
        message = {
            "type": "tool_call", 
            "payload": tool_call
        }
        # Use the communication mixin to send the message
        return await self.send_to_pilgrim(target_agent_name, message) 