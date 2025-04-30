"""
Framework Rule System Implementation

This module implements the rule loading, trigger system, and context management
for the framework rules as defined in .cursor/rules/000-framework-index.mdc
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Pattern, Optional, Any, Tuple, Callable, Awaitable
from pathlib import Path
import yaml
import asyncio
import re
from datetime import datetime, timedelta
from functools import lru_cache
import logging
from contextlib import asynccontextmanager
from fnmatch import fnmatch
from framework.mcp_server.implementations.mock_mcp_api import MockMCPAPI
from framework.mcp_server.server import MCPServer
from framework.mcp_server.server import MCPServer
import os
import json

logger = logging.getLogger(__name__)

# Define a type hint for the tool runner function
ToolRunnerType = Callable[[str, Dict[str, Any]], Awaitable[Any]]

class MCPToolIntegration:
    """MCP tool integration handler."""
    
    def __init__(self, tool_runner: Optional[ToolRunnerType] = None):
        """Initialize with an optional tool runner function."""
        self.tool_runner = tool_runner
        self.tool_cache: Dict[str, Any] = {}
        # Note: available_tools maps name to METHOD, not external function
        self.available_tools: Dict[str, Callable[[Dict[str, Any]], Awaitable[Any]]] = {
            'read_file': self._handle_read_file,
            'edit_file': self._handle_edit_file,
            'list_dir': self._handle_list_dir,
            'file_search': self._handle_file_search,
            'delete_file': self._handle_delete_file,
            'run_terminal_cmd': self._handle_terminal_cmd,
            'grep_search': self._handle_grep_search,
            'web_search': self._handle_web_search,
            'fetch_rules': self._handle_fetch_rules
        }
        
    async def trigger_tool(self, tool_name: str, params: dict) -> Any:
        """Trigger an MCP tool with given parameters using the injected runner."""
        if tool_name not in self.available_tools:
            raise ValueError(f"Unknown tool: {tool_name}")
            
        cache_key = self._get_cache_key(tool_name, params)
        if self._is_cacheable(tool_name, params) and cache_key in self.tool_cache:
            return self.tool_cache[cache_key]
            
        if self.tool_runner is None:
             # In a real scenario, might raise error or use a default if appropriate
             # For tests, this allows NameErrors if not mocked/injected.
             # Alternatively, could call the methods directly which contain the placeholder calls
             handler = self.available_tools[tool_name]
             result = await handler(params) # This will cause NameError if tool_runner not injected
        else:        
            # Use the injected tool_runner
            result = await self.tool_runner(tool_name, params)
        
        if self._is_cacheable(tool_name, params):
            self.tool_cache[cache_key] = result
            
        return result
        
    def _get_cache_key(self, tool_name: str, params: dict) -> str:
        """Generate a cache key for tool results."""
        # Use repr for potentially complex dict values in params
        return f"{tool_name}:{repr(sorted(params.items()))}"
        
    def _is_cacheable(self, tool_name: str, params: dict) -> bool:
        """Determine if tool result should be cached."""
        non_cacheable_tools = {'run_terminal_cmd', 'web_search'}
        # Example: Maybe edit_file shouldn't be cached either
        # non_cacheable_tools.add('edit_file') 
        return tool_name not in non_cacheable_tools
        
    # Internal handlers might not be needed if tool_runner is always provided,
    # but keep them for structure or potential direct calls if runner is None.
    # These will raise NameError if called without injection.
    async def _handle_read_file(self, params: dict) -> str:
        # This line assumes read_file is somehow available globally if tool_runner is None
        # which is unlikely. It will likely raise NameError.
        return await read_file(**params) 
        
    async def _handle_edit_file(self, params: dict) -> None:
        return await edit_file(**params) 
        
    async def _handle_list_dir(self, params: dict) -> List[str]:
        return await list_dir(**params) 
        
    async def _handle_file_search(self, params: dict) -> List[str]:
        return await file_search(**params) 
        
    async def _handle_delete_file(self, params: dict) -> None:
        return await delete_file(**params) 
        
    async def _handle_terminal_cmd(self, params: dict) -> str:
        return await run_terminal_cmd(**params) 
        
    async def _handle_grep_search(self, params: dict) -> List[str]:
        return await grep_search(**params) 
        
    async def _handle_web_search(self, params: dict) -> List[dict]:
        return await web_search(**params) 
        
    async def _handle_fetch_rules(self, params: dict) -> List[str]:
        return await fetch_rules(**params) 

@dataclass
class RuleMetrics:
    execution_time: float
    memory_usage: float
    trigger_count: int
    error_count: int
    last_success: Optional[datetime]
    last_error: Optional[datetime]
    tool_usage: Dict[str, int] = None  # Track MCP tool usage
    
@dataclass
class Rule:
    id: str
    path: str
    triggers: List[str]
    dependencies: List[str]
    auto_apply: bool
    last_applied: Optional[datetime] = None
    version: str = "1.0.0"
    metrics: Optional[RuleMetrics] = None
    cache_ttl: int = 300  # seconds
    mcp_integration: Optional[MCPToolIntegration] = None
    
    def __post_init__(self):
        # We need to decide how MCPToolIntegration gets the *real* tool runner
        # Maybe it's passed in when RuleLoader creates the Rule?
        # For now, initialize with None, assuming it gets set later or mocked.
        if self.mcp_integration is None:
             self.mcp_integration = MCPToolIntegration(tool_runner=None) 
        if self.metrics is None:
            self.metrics = RuleMetrics(0, 0, 0, 0, None, None, {})
            
    async def trigger_tool(self, tool_name: str, params: dict) -> Any:
        """Trigger an MCP tool and track usage."""
        if not self.mcp_integration:
            # Should not happen if __post_init__ runs
            raise RuntimeError("MCP integration not initialized for Rule") 
            
        # Track tool usage
        self.metrics.tool_usage[tool_name] = self.metrics.tool_usage.get(tool_name, 0) + 1
        
        # Delegate to the MCPIntegration instance
        return await self.mcp_integration.trigger_tool(tool_name, params)

@dataclass
class Context:
    file_path: Optional[str]
    command: Optional[str]
    active_rules: Set[str]
    parent_context: Optional['Context'] = None
    metadata: Dict[str, Any] = None
    
@dataclass
class RuleImpact:
    rule_id: str
    timestamp: datetime
    metrics: Dict[str, float]
    affected_files: List[str]
    execution_context: Dict[str, Any]
    
class RuleCache:
    def __init__(self, ttl_seconds: int = 300):
        self.cache: Dict[str, Any] = {}
        self.ttl = ttl_seconds
        
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() - entry['timestamp'] < timedelta(seconds=self.ttl):
                return entry['value']
            del self.cache[key]
        return None
        
    def set(self, key: str, value: Any) -> None:
        self.cache[key] = {
            'value': value,
            'timestamp': datetime.now()
        }
        
class RuleLoader:
    def __init__(self, rules_dir: Path, tool_runner: Optional[ToolRunnerType] = None):
        self.rules_dir = rules_dir
        self.tool_runner = tool_runner # Store the tool runner
        self.rules: Dict[str, Rule] = {}
        self.dependencies: Dict[str, List[str]] = {}
        # self.triggers is handled by Rule.triggers now
        self.cache = RuleCache()
        self.metrics: Dict[str, RuleMetrics] = {}
        # MCPIntegration is now created within Rule instances
        # self.mcp_integration = MCPToolIntegration(tool_runner=self.tool_runner)

    @asynccontextmanager
    async def rule_execution(self, rule_id: str):
        """Context manager for rule execution with metrics tracking."""
        start_time = datetime.now()
        try:
            yield
            self.metrics[rule_id] = RuleMetrics(
                execution_time=(datetime.now() - start_time).total_seconds(),
                memory_usage=0.0,  # TODO: Implement memory tracking
                trigger_count=self.metrics.get(rule_id, RuleMetrics(0, 0, 0, 0, None, None)).trigger_count + 1,
                error_count=self.metrics.get(rule_id, RuleMetrics(0, 0, 0, 0, None, None)).error_count,
                last_success=datetime.now(),
                last_error=self.metrics.get(rule_id, RuleMetrics(0, 0, 0, 0, None, None)).last_error
            )
        except Exception as e:
            self.metrics[rule_id] = RuleMetrics(
                execution_time=(datetime.now() - start_time).total_seconds(),
                memory_usage=0.0,
                trigger_count=self.metrics.get(rule_id, RuleMetrics(0, 0, 0, 0, None, None)).trigger_count,
                error_count=self.metrics.get(rule_id, RuleMetrics(0, 0, 0, 0, None, None)).error_count + 1,
                last_success=self.metrics.get(rule_id, RuleMetrics(0, 0, 0, 0, None, None)).last_success,
                last_error=datetime.now()
            )
            raise

    @lru_cache(maxsize=100)
    async def load_rules(self) -> None:
        """Load all framework rules and their relationships with caching."""
        cached_rules = self.cache.get('rules')
        if cached_rules:
            self.rules = cached_rules
            return

        try:
            index_path = self.rules_dir / '000-framework-index.mdc'
            if not index_path.exists():
                raise FileNotFoundError(f"Framework index not found at {index_path}")
                
            yaml_content = self._extract_yaml_from_mdc(index_path)
            rules_config = yaml.safe_load(yaml_content)
            
            for rule_config in rules_config['rules']:
                # Pass the tool_runner when creating MCPToolIntegration for the Rule
                mcp_integration_instance = MCPToolIntegration(tool_runner=self.tool_runner)
                rule = Rule(
                    id=rule_config['id'],
                    path=rule_config['path'],
                    triggers=[t['pattern'] for t in rule_config['triggers']], 
                    dependencies=rule_config.get('dependencies', []),
                    auto_apply=rule_config.get('autoApply', False),
                    version=rule_config.get('version', '1.0.0'),
                    cache_ttl=rule_config.get('cacheTTL', 300),
                    mcp_integration=mcp_integration_instance # Inject here
                )
                self.rules[rule.id] = rule
                self.dependencies[rule.id] = rule.dependencies
                
            self.cache.set('rules', self.rules)
        except Exception as e:
            logger.error(f"Error loading rules: {str(e)}")
            raise

    async def validate_rules(self) -> None:
        """Validate rule dependencies and triggers."""
        # Check for circular dependencies
        visited = set()
        temp_stack = set()
        
        async def check_circular(rule_id: str) -> bool:
            if rule_id in temp_stack:
                return True
            if rule_id in visited:
                return False
                
            temp_stack.add(rule_id)
            for dep in self.dependencies.get(rule_id, []):
                if await check_circular(dep):
                    return True
            temp_stack.remove(rule_id)
            visited.add(rule_id)
            return False
            
        for rule_id in self.rules:
            if await check_circular(rule_id):
                raise ValueError(f"Circular dependency detected for rule {rule_id}")
                
    async def apply_rules(self, context: Context) -> None:
        """Apply relevant rules based on context."""
        for rule_id, rule in self.rules.items():
            if rule.auto_apply and await self._should_apply_rule(rule, context):
                 # Pass the tool_runner to _apply_rule if needed, or rely on Rule's instance
                await self._apply_rule(rule, context)
                
    async def _should_apply_rule(self, rule: Rule, context: Context) -> bool:
        """Check if a rule should be applied in the current context using glob matching."""
        if not context.file_path:
            return False
            
        # Use fnmatch for glob pattern matching
        return any(
            fnmatch(context.file_path, pattern) 
            for pattern in rule.triggers
        )
        
    async def _apply_rule(self, rule: Rule, context: Context) -> None:
        """Apply a single rule to the current context with retries and MCP tool support."""
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                async with self.rule_execution(rule.id):
                    # Check if file needs to be read using the rule's mcp_integration
                    if context.file_path:
                        # Tool is triggered via the Rule instance now
                        content = await rule.trigger_tool('read_file', { 
                            'target_file': context.file_path,
                            'explanation': f"Reading file for rule {rule.id}",
                            'should_read_entire_file': False,
                            'start_line_one_indexed': 1,
                            'end_line_one_indexed_inclusive': 200
                        })
                        # Ensure metadata exists before assigning
                        if context.metadata is None: context.metadata = {} 
                        context.metadata['file_content'] = content
                    
                    # Assume rule application logic happens here
                    # This might involve calling other tools via rule.trigger_tool
                    
                    rule.last_applied = datetime.now()
                    if context.active_rules is None: context.active_rules = set()
                    context.active_rules.add(rule.id)
                    logger.info(f"Successfully applied rule {rule.id}")
                    break # Exit retry loop on success
            except Exception as e:
                logger.error(f"Error applying rule {rule.id} (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Failed to apply rule {rule.id} after {max_retries} attempts")
                    # Decide whether to re-raise or just log
                    # raise
                else:
                    await asyncio.sleep(retry_delay * (2**attempt)) # Exponential backoff

    def _extract_yaml_from_mdc(self, mdc_path: Path) -> str:
        """Extract the YAML section from an MDC file."""
        content = mdc_path.read_text()
        yaml_section = re.search(r'```yaml\n(.*?)```', content, re.DOTALL)
        if not yaml_section:
            raise ValueError(f"No YAML section found in {mdc_path}")
        return yaml_section.group(1)
        
class TriggerSystem:
    def __init__(self, rule_loader: RuleLoader):
        self.rule_loader = rule_loader
        self.active_rules: Set[str] = set()
        
    async def check_triggers(
        self,
        file_path: str,
        context: Context
    ) -> List[str]:
        """Check which rules should be triggered using Path.match."""
        logger.debug(f"Checking triggers for file: {file_path}")
        triggered = []
        if not self.rule_loader.rules:
             logger.warning("TriggerSystem: RuleLoader has no rules loaded!")
             return []
             
        try:
            # Convert the file_path string to a Path object once
            file_path_obj = Path(file_path)
        except Exception as e:
            logger.error(f"Could not create Path object from file_path '{file_path}': {e}")
            return [] # Cannot proceed if path is invalid

        for rule_id, rule in self.rule_loader.rules.items():
            logger.debug(f"  Checking rule '{rule_id}' with triggers: {rule.triggers}")
            rule_triggered = False # Flag for this rule
            try:
                for pattern in rule.triggers:
                    # Use Path.match instead of fnmatch
                    match_result = file_path_obj.match(pattern)
                    logger.debug(f"    - Matching '{file_path}' against pattern '{pattern}' using Path.match: {match_result}") 
                    if match_result:
                        rule_triggered = True
                        break 
                        
                if rule_triggered:
                    logger.debug(f"    -> Matched trigger for rule '{rule_id}'")
                    triggered.append(rule_id)
            except Exception as e:
                 logger.error(f"Error during Path.match for rule {rule_id}, file {file_path}: {e}") 
                 
        logger.debug(f"Trigger check complete for {file_path}. Triggered: {triggered}")
        return triggered
        
    async def activate_rules(
        self,
        triggered_rules: List[str]
    ) -> None:
        """Activate triggered rules and their dependencies."""
        to_activate = set()
        
        async def add_with_deps(rule_id: str):
            if rule_id not in to_activate:
                to_activate.add(rule_id)
                for dep in self.rule_loader.dependencies.get(rule_id, []):
                    await add_with_deps(dep)
                    
        for rule_id in triggered_rules:
            await add_with_deps(rule_id)
            
        self.active_rules.update(to_activate)
        
class ContextManager:
    def __init__(self):
        self.current_context: Optional[Context] = None
        self.context_history: List[Context] = []
        
    async def push_context(self, context: Context) -> None:
        """Push a new context onto the stack."""
        context.parent_context = self.current_context
        self.current_context = context
        self.context_history.append(context)
        
    async def pop_context(self) -> Optional[Context]:
        """Pop the current context from the stack."""
        if not self.current_context:
            return None
            
        old_context = self.current_context
        self.current_context = self.current_context.parent_context
        return old_context
        
class IDEIntegration:
    def __init__(self, rules_dir: Path, tool_runner: Optional[ToolRunnerType] = None):
        # Pass tool_runner to RuleLoader
        self.rule_loader = RuleLoader(rules_dir, tool_runner=tool_runner) 
        self.trigger_system = TriggerSystem(self.rule_loader)
        self.context_manager = ContextManager()
        
    async def initialize(self) -> None:
        """Initialize the IDE integration."""
        await self.rule_loader.load_rules()
        await self.rule_loader.validate_rules()
        
    async def on_file_change(self, file_path: str) -> None:
        """Handle file change events."""
        context = Context(
            file_path=file_path,
            command=None,
            active_rules=set()
        )
        await self.context_manager.push_context(context)
        
        triggered_rules = await self.trigger_system.check_triggers(
            file_path,
            context
        )
        await self.trigger_system.activate_rules(triggered_rules)
        await self.rule_loader.apply_rules(context)
        
    async def on_command(self, command: str) -> None:
        """Handle command execution events."""
        context = Context(
            file_path=None,
            command=command,
            active_rules=set()
        )
        await self.context_manager.push_context(context)
        await self.rule_loader.apply_rules(context)
        
class FrameworkIntegration:
    def __init__(self, ide_integration: IDEIntegration):
        self.ide_integration = ide_integration
        self.impact_history: List[RuleImpact] = []
        
    async def apply_framework_rules(self, context: Context) -> None:
        """Apply framework rules to current context."""
        await self.ide_integration.rule_loader.apply_rules(context)
        
    async def track_rule_impact(
        self,
        rule_id: str,
        impact: RuleImpact
    ) -> None:
        """Track the impact of applied rules."""
        self.impact_history.append(impact)
        
class HealthMonitor:
    def __init__(self, rule_loader: RuleLoader):
        self.rule_loader = rule_loader
        self.health_metrics: Dict[str, Dict[str, Any]] = {}
        
    async def check_health(self) -> Dict[str, Any]:
        """Check the health of the rule system."""
        metrics = {
            'total_rules': len(self.rule_loader.rules),
            'active_rules': len([r for r in self.rule_loader.rules.values() if r.last_applied]),
            'error_rate': self._calculate_error_rate(),
            'performance': self._calculate_performance_metrics(),
            'memory_usage': self._calculate_memory_usage(),
            'rule_metrics': self.rule_loader.metrics
        }
        return metrics
        
    def _calculate_error_rate(self) -> float:
        total_errors = sum(m.error_count for m in self.rule_loader.metrics.values())
        total_triggers = sum(m.trigger_count for m in self.rule_loader.metrics.values())
        return total_errors / total_triggers if total_triggers > 0 else 0.0
        
    def _calculate_performance_metrics(self) -> Dict[str, float]:
        execution_times = [m.execution_time for m in self.rule_loader.metrics.values()]
        return {
            'avg_execution_time': sum(execution_times) / len(execution_times) if execution_times else 0.0,
            'max_execution_time': max(execution_times) if execution_times else 0.0,
            'min_execution_time': min(execution_times) if execution_times else 0.0
        }
        
    def _calculate_memory_usage(self) -> Dict[str, float]:
        memory_usage = [m.memory_usage for m in self.rule_loader.metrics.values()]
        return {
            'total_memory': sum(memory_usage),
            'avg_memory': sum(memory_usage) / len(memory_usage) if memory_usage else 0.0
        }

# Updated initialize_rule_system to accept and pass tool_runner
async def initialize_rule_system(rules_dir: Path, tool_runner: Optional[ToolRunnerType] = None) -> Tuple[IDEIntegration, HealthMonitor]:
    """Initialize the rule system with health monitoring and tool runner."""
    # Pass tool_runner to IDEIntegration
    ide_integration = IDEIntegration(rules_dir, tool_runner=tool_runner)
    await ide_integration.initialize()
    health_monitor = HealthMonitor(ide_integration.rule_loader)
    return ide_integration, health_monitor 