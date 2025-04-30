"""
MCP Server Implementation

This module implements the core MCP server functionality.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from .tools import ToolCategory, ToolDefinition, ToolResult

logger = logging.getLogger(__name__)

class MCPServer:
    """MCP Server implementation."""
    
    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self.tool_implementations: Dict[str, Callable] = {}
        self.results_cache: Dict[str, ToolResult] = {}
        self.rate_limits: Dict[str, List[datetime]] = {}
        self._running = False
        self._tasks = []
        
    async def start(self):
        """Start the MCP server."""
        if self._running:
            return
            
        self._running = True
        logger.info("Starting MCP server")
        self._tasks = []
        
        # Start background tasks
        self._tasks.append(asyncio.create_task(self._cache_cleanup()))
        self._tasks.append(asyncio.create_task(self._rate_limit_cleanup()))
        
    async def stop(self):
        """Stop the MCP server."""
        if not self._running:
            return
            
        self._running = False
        logger.info("Stopping MCP server")
        
        # Cancel all background tasks
        for task in self._tasks:
            task.cancel()
            
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        
    async def register_tool(self, tool_def: ToolDefinition, implementation: Callable) -> None:
        """Register a new tool with its implementation."""
        if tool_def.name in self.tools:
            raise ValueError(f"Tool already registered: {tool_def.name}")
            
        self.tools[tool_def.name] = tool_def
        self.tool_implementations[tool_def.name] = implementation
        logger.info(f"Registered tool: {tool_def.name}")
        
    async def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> ToolResult:
        """Execute a tool with given parameters."""
        if not self._running:
            raise RuntimeError("MCP server is not running")
            
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
            
        tool = self.tools[tool_name]
        implementation = self.tool_implementations[tool_name]
        
        # Validate required parameters
        for required in tool.required_params:
            if required not in params:
                raise ValueError(f"Missing required parameter: {required}")
                
        # Check rate limit
        if tool.rate_limit:
            await self._check_rate_limit(tool_name, tool.rate_limit)
            
        # Check cache
        if tool.cache_ttl:
            cache_key = self._get_cache_key(tool_name, params)
            cached = self.results_cache.get(cache_key)
            if cached and (datetime.now() - cached.timestamp).total_seconds() < tool.cache_ttl:
                return cached
                
        # Execute tool
        start_time = datetime.now()
        try:
            result = await implementation(**params)
            status = "success"
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name}", exc_info=e)
            status = "error"
            result = str(e)
            
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Create tool result
        tool_result = ToolResult(
            tool_name=tool_name,
            status=status,
            result=result,
            execution_time=execution_time,
            timestamp=datetime.now(),
            metadata={"params": params}
        )
        
        # Cache result if applicable
        if tool.cache_ttl and status == "success":
            cache_key = self._get_cache_key(tool_name, params)
            self.results_cache[cache_key] = tool_result
            
        # Update rate limit tracking
        if tool.rate_limit:
            self.rate_limits.setdefault(tool_name, []).append(datetime.now())
            
        return tool_result
        
    def _get_cache_key(self, tool_name: str, params: Dict[str, Any]) -> str:
        """Generate a cache key for tool results."""
        sorted_params = sorted(params.items())
        return f"{tool_name}:{str(sorted_params)}"
        
    async def _check_rate_limit(self, tool_name: str, rate_limit: int) -> None:
        """Check if tool execution is allowed by rate limit."""
        if tool_name not in self.rate_limits:
            return
            
        now = datetime.now()
        recent_calls = [t for t in self.rate_limits[tool_name]
                       if (now - t).total_seconds() < 60]
                       
        if len(recent_calls) >= rate_limit:
            raise RuntimeError(f"Rate limit exceeded for tool: {tool_name}")
            
    async def _cache_cleanup(self):
        """Periodically clean up expired cache entries."""
        while self._running:
            now = datetime.now()
            for tool_name, tool in self.tools.items():
                if not tool.cache_ttl:
                    continue
                    
                cache_keys = [k for k in self.results_cache.keys()
                            if k.startswith(f"{tool_name}:")]
                            
                for key in cache_keys:
                    result = self.results_cache[key]
                    if (now - result.timestamp).total_seconds() >= tool.cache_ttl:
                        del self.results_cache[key]
                        
            await asyncio.sleep(60)  # Clean up every minute
            
    async def _rate_limit_cleanup(self):
        """Periodically clean up old rate limit entries."""
        while self._running:
            now = datetime.now()
            for tool_name in list(self.rate_limits.keys()):
                self.rate_limits[tool_name] = [
                    t for t in self.rate_limits[tool_name]
                    if (now - t).total_seconds() < 60
                ]
                
            await asyncio.sleep(60)  # Clean up every minute 