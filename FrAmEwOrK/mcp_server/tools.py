"""
MCP Server Tools

This module defines the tool categories, definitions, and base classes.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime

class ToolCategory(Enum):
    """Categories of MCP tools."""
    FILE = "file"
    TERMINAL = "terminal"
    WEB = "web"
    AI = "ai"
    DATABASE = "db"
    VECTOR = "vector"
    AGENT = "agent"
    SYSTEM = "system"

@dataclass
class ToolDefinition:
    """Definition of an MCP tool."""
    name: str
    category: ToolCategory
    description: str
    parameters: Dict[str, Any]
    required_params: List[str]
    is_async: bool = True
    cache_ttl: Optional[int] = None
    rate_limit: Optional[int] = None
    version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ToolResult:
    """Result of a tool execution."""
    tool_name: str
    status: str
    result: Any
    execution_time: float
    timestamp: datetime
    metadata: Dict[str, Any]

# Essential Agent Tools

FILE_TOOLS = [
    ToolDefinition(
        name="read_file",
        category=ToolCategory.FILE,
        description="Read file contents with optional line range",
        parameters={
            "path": "str",
            "start_line": "Optional[int]",
            "end_line": "Optional[int]"
        },
        required_params=["path"],
        cache_ttl=60
    ),
    ToolDefinition(
        name="write_file",
        category=ToolCategory.FILE,
        description="Write content to a file",
        parameters={
            "path": "str",
            "content": "str",
            "mode": "str"
        },
        required_params=["path", "content"]
    ),
    ToolDefinition(
        name="list_dir",
        category=ToolCategory.FILE,
        description="List directory contents",
        parameters={
            "path": "str",
            "recursive": "bool"
        },
        required_params=["path"],
        cache_ttl=30
    )
]

AI_TOOLS = [
    ToolDefinition(
        name="text_embedding",
        category=ToolCategory.AI,
        description="Generate embeddings for text",
        parameters={
            "text": "str",
            "model": "str"
        },
        required_params=["text"],
        cache_ttl=3600,
        rate_limit=100
    ),
    ToolDefinition(
        name="code_analysis",
        category=ToolCategory.AI,
        description="Analyze code for patterns and issues",
        parameters={
            "code": "str",
            "language": "str",
            "context": "Optional[Dict[str, Any]]"
        },
        required_params=["code"],
        cache_ttl=1800,
        rate_limit=50
    ),
    ToolDefinition(
        name="semantic_search",
        category=ToolCategory.AI,
        description="Perform semantic search on text",
        parameters={
            "query": "str",
            "corpus": "List[str]",
            "top_k": "int"
        },
        required_params=["query", "corpus"],
        cache_ttl=300
    ),
    ToolDefinition(
        name="layer_thought_process",
        category=ToolCategory.AI,
        description="Process input through layers of thought",
        parameters={
            "input_data": "Any",
            "context": "Dict[str, Any]",
            "layer_sequence": "List[str]"
        },
        required_params=["input_data", "layer_sequence"],
        cache_ttl=None,  # Don't cache thought processes
        rate_limit=20,
        metadata={
            "layer_types": [
                "perception",
                "reasoning",
                "planning",
                "execution",
                "reflection"
            ],
            "supports_triggers": True,
            "maintains_context": True
        }
    )
]

VECTOR_TOOLS = [
    ToolDefinition(
        name="vector_store_query",
        category=ToolCategory.VECTOR,
        description="Query vector store for similar items",
        parameters={
            "collection": "str",
            "query_vector": "List[float]",
            "top_k": "int"
        },
        required_params=["collection", "query_vector"],
        cache_ttl=60
    ),
    ToolDefinition(
        name="vector_store_update",
        category=ToolCategory.VECTOR,
        description="Update vectors in the store",
        parameters={
            "collection": "str",
            "vectors": "List[List[float]]",
            "metadata": "List[Dict[str, Any]]"
        },
        required_params=["collection", "vectors"]
    ),
    ToolDefinition(
        name="similarity_search",
        category=ToolCategory.VECTOR,
        description="Find similar items using vector similarity",
        parameters={
            "query": "List[float]",
            "candidates": "List[List[float]]",
            "metric": "str"
        },
        required_params=["query", "candidates"],
        cache_ttl=300
    )
]

AGENT_TOOLS = [
    ToolDefinition(
        name="agent_create",
        category=ToolCategory.AGENT,
        description="Create a new agent",
        parameters={
            "agent_type": "str",
            "config": "Dict[str, Any]"
        },
        required_params=["agent_type"]
    ),
    ToolDefinition(
        name="agent_execute",
        category=ToolCategory.AGENT,
        description="Execute an agent task",
        parameters={
            "agent_id": "str",
            "task": "Dict[str, Any]"
        },
        required_params=["agent_id", "task"]
    ),
    ToolDefinition(
        name="agent_status",
        category=ToolCategory.AGENT,
        description="Get agent status",
        parameters={
            "agent_id": "str"
        },
        required_params=["agent_id"],
        cache_ttl=5
    )
]

SYSTEM_TOOLS = [
    ToolDefinition(
        name="system_info",
        category=ToolCategory.SYSTEM,
        description="Get system information",
        parameters={},
        required_params=[],
        cache_ttl=300
    ),
    ToolDefinition(
        name="system_metrics",
        category=ToolCategory.SYSTEM,
        description="Get system metrics",
        parameters={
            "metrics": "List[str]"
        },
        required_params=["metrics"],
        cache_ttl=10
    )
]

# All available tools
ALL_TOOLS = (
    FILE_TOOLS +
    AI_TOOLS +
    VECTOR_TOOLS +
    AGENT_TOOLS +
    SYSTEM_TOOLS
) 