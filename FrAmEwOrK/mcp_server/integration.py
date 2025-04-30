"""
MCP Server Integration

This module provides integration between MCP tools and the framework/agents.
"""

import logging
from typing import Dict, List, Any, Optional, Type
from .server import MCPServer
from .tools import (
    ToolCategory,
    ToolDefinition,
    ToolResult,
    ALL_TOOLS
)

logger = logging.getLogger(__name__)

class FrameworkMCPIntegration:
    """Framework integration for MCP tools."""
    
    def __init__(self):
        self.server = MCPServer()
        self.active_tools: Dict[str, bool] = {}
        self.tool_implementations: Dict[str, Any] = {}
        
    async def initialize(self):
        """Initialize MCP server integration."""
        await self.server.start()
        
        # Register all tools
        for tool in ALL_TOOLS:
            implementation = self._get_tool_implementation(tool)
            if implementation:
                await self.server.register_tool(tool, implementation)
                self.active_tools[tool.name] = True
                
    async def shutdown(self):
        """Shutdown MCP server integration."""
        await self.server.stop()
        
    def _get_tool_implementation(self, tool: ToolDefinition) -> Optional[Any]:
        """Get the implementation for a tool."""
        if tool.name in self.tool_implementations:
            return self.tool_implementations[tool.name]
            
        # Import and return tool implementation
        try:
            module_name = f"framework.mcp_server.implementations.{tool.category.value}"
            module = __import__(module_name, fromlist=[tool.name])
            implementation = getattr(module, tool.name)
            self.tool_implementations[tool.name] = implementation
            return implementation
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load implementation for tool {tool.name}: {e}")
            return None
            
    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Execute an MCP tool."""
        result = await self.server.execute_tool(tool_name, params)
        return result.result
        
class AgentMCPInterface:
    """Agent interface for MCP tools."""
    
    def __init__(self, framework_mcp: FrameworkMCPIntegration):
        self.framework_mcp = framework_mcp
        self.agent_id: Optional[str] = None
        self.tool_usage: Dict[str, int] = {}
        
    async def initialize(self, agent_id: str):
        """Initialize the agent interface."""
        self.agent_id = agent_id
        
    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Execute an MCP tool on behalf of an agent."""
        if not self.agent_id:
            raise RuntimeError("Agent interface not initialized")
            
        # Add agent context to params
        params["agent_id"] = self.agent_id
        
        # Track tool usage
        self.tool_usage[tool_name] = self.tool_usage.get(tool_name, 0) + 1
        
        try:
            return await self.framework_mcp.execute_tool(tool_name, params)
        except Exception as e:
            logger.error(f"Tool execution failed for agent {self.agent_id}: {e}")
            raise
            
    def get_available_tools(self) -> List[ToolDefinition]:
        """Get list of available tools."""
        return [tool for tool in ALL_TOOLS
                if tool.name in self.framework_mcp.active_tools]
                
    def get_tool_usage(self) -> Dict[str, int]:
        """Get tool usage statistics."""
        return self.tool_usage.copy()
        
class AgentToolRegistry:
    """Registry for agent-specific tool implementations."""
    
    def __init__(self):
        self.implementations: Dict[str, Dict[Type, Any]] = {}
        
    def register_implementation(
        self,
        tool_name: str,
        agent_type: Type,
        implementation: Any
    ) -> None:
        """Register a tool implementation for a specific agent type."""
        if tool_name not in self.implementations:
            self.implementations[tool_name] = {}
        self.implementations[tool_name][agent_type] = implementation
        
    def get_implementation(
        self,
        tool_name: str,
        agent_type: Type
    ) -> Optional[Any]:
        """Get tool implementation for a specific agent type."""
        return (self.implementations.get(tool_name, {})
                .get(agent_type))
                
    def get_supported_tools(self, agent_type: Type) -> List[str]:
        """Get list of tools supported by an agent type."""
        return [tool_name for tool_name, impls in self.implementations.items()
                if agent_type in impls] 