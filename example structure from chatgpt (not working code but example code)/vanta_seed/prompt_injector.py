# === prompt_injector.py ===

"""
PromptInjector
Handles injecting context and identity into AI prompts.
"""

class PromptInjector:
    def __init__(self, identity, collapse, rituals, plugins):
        self.identity = identity
        self.collapse = collapse
        self.rituals = rituals
        self.plugins = plugins
        print("PromptInjector initialized.")

    def inject(self, user_input, context=None):
        """
        Build and return the injected prompt.
        """
        print("PromptInjector → Injecting prompt.")

        identity_description = self.identity.describe_self()
        collapsed_context = self.collapse.apply(context or {})

        injected_prompt = f"""[Identity]: {identity_description}

[Context]: {collapsed_context}

[User Input]: {user_input}
"""

        ritualized = self.rituals.apply_rituals(user_input)
        if ritualized:
            injected_prompt += f"\n[Ritual]: {ritualized}"

        print("PromptInjector → Prompt injection complete.")
        return injected_prompt
