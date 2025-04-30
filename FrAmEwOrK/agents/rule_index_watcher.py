"""
Rule Index Watcher Agent

This agent monitors the rules directory for changes and maintains the framework index.
"""

import os
import asyncio
import json
import yaml
import hashlib
from typing import Dict, List, Optional, Set
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent
from datetime import datetime
from dataclasses import dataclass
import re
import logging

logger = logging.getLogger(__name__)

@dataclass
class RuleMetadata:
    """Metadata for a framework rule."""
    id: str
    path: str
    triggers: List[str]
    dependencies: List[str]
    auto_apply: bool
    last_modified: float
    hash: str
    validation_errors: List[str]

class RuleChangeHandler(FileSystemEventHandler):
    """Handles file system events for rule changes."""
    
    def __init__(self, watcher_agent: 'RuleIndexWatcherAgent'):
        self.agent = watcher_agent
        
    def on_created(self, event):
        if event.src_path.endswith('.mdc'):
            asyncio.create_task(self.agent.handle_rule_created(event.src_path))
            
    def on_modified(self, event):
        if event.src_path.endswith('.mdc'):
            asyncio.create_task(self.agent.handle_rule_modified(event.src_path))
            
    def on_deleted(self, event):
        if event.src_path.endswith('.mdc'):
            asyncio.create_task(self.agent.handle_rule_deleted(event.src_path))

class RuleIndexWatcherAgent(FileSystemEventHandler):
    """
    Agent responsible for monitoring the rules directory and maintaining the framework index.
    
    Features:
    - Watches for new, modified, or deleted rule files
    - Updates the framework index automatically
    - Validates rule format and structure
    - Maintains rule dependencies
    - Logs all changes for audit
    """
    
    def __init__(self, rules_dir: str = ".cursor/rules"):
        self.rules_dir = Path(rules_dir)
        self.index_file = self.rules_dir / "000-framework-index.mdc"
        self.observer = Observer()
        self.handler = RuleChangeHandler(self)
        self.rules: Dict[str, RuleMetadata] = {}
        self.dependency_graph: Dict[str, Set[str]] = {}
        self._rule_cache: Dict[str, str] = {}  # Cache of rule file contents
        self.validation_lock = asyncio.Lock()
        self.is_running = False
        
    async def start(self):
        """Start monitoring the rules directory."""
        if self.is_running:
            return
            
        # Initial load of current rules
        await self.load_all_rules()
        
        # Start watching for changes
        self.observer.schedule(self, str(self.rules_dir), recursive=True)
        self.observer.start()
        self.is_running = True
        
        print(f"RuleIndexWatcherAgent started watching {self.rules_dir}")
        
    async def stop(self):
        """Stop monitoring the rules directory."""
        if not self.is_running:
            return
            
        self.observer.stop()
        self.observer.join()
        self.is_running = False
        
    async def load_all_rules(self):
        """Load all rules from the rules directory."""
        async with self.validation_lock:
            for root, _, files in os.walk(str(self.rules_dir)):
                for file in files:
                    if file.endswith('.mdc'):
                        # Explicitly skip the index file itself
                        if file == "000-framework-index.mdc":
                            continue 
                        path = os.path.join(root, file)
                        await self.handle_rule_change(path)
                    
    async def handle_rule_change(self, path: str):
        """Handle a rule file being created or modified."""
        logger.debug(f"handle_rule_change called for: {path}")
        try:
            rule_content = await self.read_rule_file(path)
            rule_hash = self.compute_rule_hash(rule_content)
            
            logger.debug(f"  File: {path}, New Hash: {rule_hash}")
            cached_hash = self._rule_cache.get(path)
            logger.debug(f"  Cached Hash: {cached_hash}")

            # --- Restore Cache Check --- 
            if path in self._rule_cache and self._rule_cache[path] == rule_hash:
                logger.debug(f"  Skipping unchanged rule (hash match): {path}")
                return
            # ---------------------------
            
            logger.debug(f"  Updating cache for {path} with hash {rule_hash}")
            self._rule_cache[path] = rule_hash # Update cache
            rule_data = await self.parse_rule_file(rule_content)
            
            if not rule_data:
                logger.warning(f"Could not parse rule file {path}, skipping update.")
                # Optionally remove from self.rules if it existed before but is now invalid
                rule_id_from_path = self.get_rule_id(path)
                if rule_id_from_path in self.rules:
                    logger.info(f"Removing previously valid rule {rule_id_from_path} due to parsing failure.")
                    del self.rules[rule_id_from_path]
                    # Consider calling update_dependency_graph and update_index here too
                return

            rule_id = rule_data.get('id') # Use get to avoid KeyError if id missing
            if not rule_id:
                 # If parse_rule_file didn't catch this, maybe it should?
                 # For now, use path stem as fallback ID, but log warning.
                 logger.warning(f"Rule data for {path} missing 'id'. Using filename stem as ID.")
                 rule_id = self.get_rule_id(path)
            
            # Log state *before* creating/updating RuleMetadata
            existing_rule = self.rules.get(rule_id)
            logger.debug(f"  Existing rule data for '{rule_id}': {existing_rule}")

            # Correctly extract string patterns from the list of dicts
            trigger_list = rule_data.get('triggers', [])
            triggers = [t.get('pattern', '') for t in trigger_list if isinstance(t, dict) and 'pattern' in t]
            logger.debug(f"  Parsed triggers: {triggers}")

            metadata = RuleMetadata(
                id=rule_id,
                path=path,
                triggers=triggers, # Use the extracted list of strings
                dependencies=rule_data.get('dependencies', []),
                auto_apply=rule_data.get('autoApply', False),
                last_modified=os.path.getmtime(path),
                hash=rule_hash,
                validation_errors=[] # Validation happens next
            )

            logger.debug(f"  Created metadata object: {metadata}")

            validation_errors = await self.validate_rule(metadata)
            metadata.validation_errors = validation_errors
            logger.debug(f"  Validation errors: {validation_errors}")

            self.rules[rule_id] = metadata
            logger.debug(f"  Updated self.rules[{rule_id}]: {self.rules[rule_id]}")
            
            # Check dependencies and update index AFTER updating self.rules
            await self.update_dependency_graph()
            await self.update_index() 
            logger.debug(f"handle_rule_change finished for: {path}")

        except Exception as e:
            logger.exception(f"Error handling rule change for {path}: {e}")

    async def handle_rule_created(self, file_path: str):
        """Handle creation of a new rule file."""
        path = Path(file_path)
        if rule_data := await self.parse_rule_file(path):
            self.rules[rule_data['name']] = rule_data
            await self.update_index()
            print(f"Added new rule: {path.name}")
            
    async def handle_rule_modified(self, file_path: str):
        """Handle modification of an existing rule file."""
        path = Path(file_path)
        if rule_data := await self.parse_rule_file(path):
            self.rules[rule_data['name']] = rule_data
            await self.update_index()
            print(f"Updated rule: {path.name}")
            
    async def handle_rule_deleted(self, file_path: str):
        """Handle deletion of a rule file."""
        path = Path(file_path)
        rule_id = path.stem
        if rule_id in self.rules:
            del self.rules[rule_id]
            await self.update_index()
            print(f"Removed rule: {path.name}")
            
    async def validate_rules(self) -> List[str]:
        """Validate all rules for proper format and dependencies."""
        errors = []
        for rule_id, rule in self.rules.items():
            # Check required metadata
            if 'metadata' not in rule:
                errors.append(f"Rule {rule_id} missing metadata")
                continue
                
            metadata = rule['metadata']
            if 'description' not in metadata:
                errors.append(f"Rule {rule_id} missing description")
                
            if 'type' not in metadata:
                errors.append(f"Rule {rule_id} missing type")
                
        return errors
        
    async def get_rule_dependencies(self) -> Dict[str, Set[str]]:
        """Analyze and return rule dependencies."""
        dependencies = {}
        for rule_id, rule in self.rules.items():
            dependencies[rule_id] = set()
            if 'metadata' in rule and 'dependencies' in rule['metadata']:
                dependencies[rule_id].update(rule['metadata']['dependencies'])
        return dependencies

    async def validate_rule(self, rule: RuleMetadata) -> List[str]:
        """Validate a rule's structure and dependencies."""
        errors = []
        
        # Check for required fields
        if not rule.id:
            errors.append("Rule ID is required")
        if not rule.path:
            errors.append("Rule path is required")
            
        # Validate dependencies
        for dep in rule.dependencies:
            if dep not in self.rules and dep != rule.id:
                errors.append(f"Dependency '{dep}' not found")
                
        # Check for circular dependencies
        if await self.has_circular_dependency(rule.id, set()):
            errors.append("Circular dependency detected")
            
        # Validate trigger patterns (now strings)
        for trigger in rule.triggers:
            if not isinstance(trigger, str) or not trigger:
                errors.append(f"Invalid trigger pattern (must be non-empty string): {trigger}")
            # Optional: Add basic glob syntax validation here if needed
                
        return errors

    async def has_circular_dependency(self, rule_id: str, visited: Set[str]) -> bool:
        """Check if a rule has circular dependencies."""
        if rule_id in visited:
            return True
        
        visited.add(rule_id)
        if rule_id in self.rules:
            for dep in self.rules[rule_id].dependencies:
                if await self.has_circular_dependency(dep, visited.copy()):
                    return True
        return False

    async def update_dependency_graph(self):
        """Update the dependency graph for all rules."""
        new_graph: Dict[str, Set[str]] = {}
        
        for rule_id, rule in self.rules.items():
            new_graph[rule_id] = set(rule.dependencies)
            
        # Validate the new graph
        for rule_id in new_graph:
            visited = set()
            if await self.has_circular_dependency(rule_id, visited):
                print(f"Warning: Circular dependency detected for rule {rule_id}")
                continue
                
        self.dependency_graph = new_graph

    async def reindex_rules(self):
        """Reindex all rules based on the framework index."""
        index_path = os.path.join(str(self.rules_dir), '000-framework-index.mdc')
        if not os.path.exists(index_path):
            return

        try:
            index_content = await self.read_rule_file(index_path)
            index_data = await self.parse_rule_file(index_content)
            
            if not index_data or 'rules' not in index_data:
                return
                
            # Update rules based on index
            for rule in index_data['rules']:
                rule_path = os.path.join(str(self.rules_dir), rule['path'])
                if os.path.exists(rule_path):
                    await self.handle_rule_change(rule_path)

        except Exception as e:
            print(f"Error reindexing rules: {str(e)}")

    @staticmethod
    def get_rule_id(path: str) -> str:
        """Get a rule ID from its file path."""
        return os.path.splitext(os.path.basename(path))[0]

    @staticmethod
    def compute_rule_hash(content: str) -> str:
        """Compute a hash of the rule content."""
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    async def read_rule_file(path: str) -> str:
        """Read a rule file's contents."""
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    def _extract_yaml_from_mdc(mdc_path: Path) -> Optional[str]:
        """Extract the YAML section from an MDC file."""
        try:
            content = mdc_path.read_text()
            # Use a more robust regex allowing for optional spaces/newlines around delimiters
            match = re.search(r'^---\s*\n(.*?)\n---\s*$', content, re.DOTALL | re.MULTILINE)
            if match:
                return match.group(1)
            else:
                # Fallback for simple triple-dash if first fails
                match = re.search(r'---\n(.*?)\n---', content, re.DOTALL)
                if match:
                    return match.group(1)
            return None # No YAML found
        except Exception as e:
            print(f"Error reading/parsing MDC for YAML: {mdc_path} - {e}")
            return None

    @staticmethod
    async def parse_rule_file(content: str) -> Optional[Dict]:
        """Parse rule metadata from file content."""
        try:
            match = re.search(r'^---\s*\n(.*?)\n---\s*$', content, re.DOTALL | re.MULTILINE)
            if not match:
                match = re.search(r'---\n(.*?)\n---', content, re.DOTALL)
            
            if not match:
                 print(f"Warning: Could not find YAML front matter in content.")
                 return None

            metadata_str = match.group(1).strip()
            metadata = yaml.safe_load(metadata_str)

            if not isinstance(metadata, dict):
                 print(f"Warning: Parsed YAML is not a dictionary.")
                 return None
                 
            if 'id' not in metadata: 
                print(f"Warning: Rule metadata missing 'id' field.")
                return None 
                 
            return metadata
        except yaml.YAMLError as e:
            print(f"Warning: YAML parsing error: {e}")
            return None
        except Exception as e:
            print(f"Warning: Unexpected error parsing rule file: {e}")
            return None

    async def update_index(self):
        """Update the 000-framework-index.mdc file."""
        # ... (logic to rebuild index YAML from self.rules)
        # Important: Ensure this generates the YAML in the expected format
        # with triggers like [{'pattern': '*.py'}], etc.
        
        index_data = {
            'description': 'Framework Rule Index', # Or load existing description
            'rules': []
        }
        
        # Sort rules by ID for consistent output
        for rule_id in sorted(self.rules.keys()):
            rule = self.rules[rule_id]
            index_data['rules'].append({
                'id': rule.id,
                'path': os.path.relpath(rule.path, self.rules_dir.parent).replace('\\', '/'), # Relative path
                # Reconstruct the original trigger format for YAML
                'triggers': [{'pattern': p} for p in rule.triggers],
                'dependencies': rule.dependencies,
                'autoApply': rule.auto_apply
                # Add other fields like version if needed in index
            })
            
        try:
            # Keep existing content outside the YAML block if possible
            existing_content = ""
            if self.index_file.exists():
                existing_content = self.index_file.read_text()
                
            # Find content before and after the YAML block
            pre_yaml = ""
            post_yaml = ""
            yaml_match_pre = re.match(r'^(.*?)---\s*\n', existing_content, re.DOTALL)
            if yaml_match_pre:
                pre_yaml = yaml_match_pre.group(1)
                
            yaml_match_post = re.search(r'\n---\s*$(.*)', existing_content, re.DOTALL)
            if yaml_match_post:
                post_yaml = yaml_match_post.group(1)
                
            # If no YAML block found, use defaults
            if not pre_yaml and not post_yaml and existing_content:
                 pre_yaml = existing_content # Assume all content was before non-existent YAML
            elif not pre_yaml and not post_yaml: # Handle empty or new file
                 pre_yaml = "# Framework Rules Index\n# ... (Default header comments) ...\n\n" # Add default header

            # Use safe_dump with explicit start/end markers and default_flow_style=False
            yaml_string = yaml.safe_dump(index_data, default_flow_style=False, sort_keys=False)
            
            new_index_content = f"{pre_yaml.strip()}\n---\n{yaml_string.strip()}\n---\n{post_yaml.strip()}".strip() + "\n"

            # Only write if content has changed
            if not self.index_file.exists() or self.index_file.read_text() != new_index_content:
                self.index_file.write_text(new_index_content)
                print("Framework index updated.")
                
        except Exception as e:
            print(f"Error updating index file: {str(e)}")

    def get_active_rules(self) -> List[str]:
        """Get a list of currently active rules."""
        return [rule_id for rule_id, rule in self.rules.items() 
                if not rule.validation_errors and rule.auto_apply]

    def get_rule_dependencies(self, rule_id: str) -> List[str]:
        """Get all dependencies for a rule, including transitive dependencies."""
        if rule_id not in self.dependency_graph:
            return []
            
        deps = set()
        to_process = list(self.dependency_graph[rule_id])
        
        while to_process:
            dep = to_process.pop()
            if dep not in deps:
                deps.add(dep)
                if dep in self.dependency_graph:
                    to_process.extend(self.dependency_graph[dep])
                    
        return list(deps)

    async def get_rule_status(self) -> Dict:
        """Get the current status of all rules."""
        return {
            'total_rules': len(self.rules),
            'active_rules': len(self.get_active_rules()),
            'rules_with_errors': sum(1 for rule in self.rules.values() if rule.validation_errors),
            'dependency_chains': len(self.dependency_graph),
            'rules': {
                rule_id: {
                    'path': rule.path,
                    'auto_apply': rule.auto_apply,
                    'last_modified': rule.last_modified,
                    'validation_errors': rule.validation_errors,
                    'dependencies': self.get_rule_dependencies(rule_id)
                } for rule_id, rule in self.rules.items()
            }
        }

# Example usage:
async def main():
    agent = RuleIndexWatcherAgent()
    await agent.start()
    
    try:
        # Keep the agent running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await agent.stop()

if __name__ == "__main__":
    asyncio.run(main()) 