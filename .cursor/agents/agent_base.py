"""
Base classes and typing definitions for Cursor IDE agents.
"""
from typing import Any, List, Protocol

class TriggerContext:
    """Context provided to agent triggers."""
    current_file: Any
    diff: Any
    user_query: str = ""

class Suggestion:
    """Represents a suggestion or code action to be presented by Cursor."""
    def __init__(self, title: str, edits: List[Any] = None, details: Any = None):
        self.title = title
        self.edits = edits or []
        self.details = details

class AgentBase(Protocol):
    """Protocol for IDE-level agents."""
    id: str
    name: str
    triggers: dict

    def on_file_change(self, context: TriggerContext) -> List[Suggestion]:
        ...

    def on_user_query(self, context: TriggerContext) -> List[Suggestion]:
        ...

    def on_message(self, context: TriggerContext) -> List[Suggestion]:
        ...

    def on_api_request(self, context: TriggerContext) -> List[Suggestion]:
        ... 