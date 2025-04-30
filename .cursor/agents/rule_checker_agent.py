import re
from .agent_base import AgentBase, TriggerContext, Suggestion

class RuleCheckerAgent(AgentBase):
    """IDE agent that checks code against coding-agent MDC rules and suggests fixes."""
    id = "rule_checker"
    name = "Rule Checker Agent"
    triggers = {
        "onFileChange": True,
        "onUserQuery": False,
        "onMessage": False,
        "onAPIRequest": False,
    }

    def on_file_change(self, context: TriggerContext) -> list[Suggestion]:
        suggestions: list[Suggestion] = []
        file_path = getattr(context.current_file, 'path', '')
        content = getattr(context.current_file, 'content', '')
        # Example check: ensure subprocess.run uses shell=False
        if file_path.endswith('.py') and 'subprocess.run' in content:
            # naive pattern detection
            if 'shell=True' in content:
                suggestions.append(
                    Suggestion(
                        title="Use shell=False for subprocess.run",
                        details="Avoid shell=True to prevent injection; pass args list.",
                    )
                )
        # TODO: Load and apply all coding-agent rule patterns
        return suggestions

    def on_user_query(self, context: TriggerContext) -> list[Suggestion]:
        return []

    def on_message(self, context: TriggerContext) -> list[Suggestion]:
        return []

    def on_api_request(self, context: TriggerContext) -> list[Suggestion]:
        return [] 