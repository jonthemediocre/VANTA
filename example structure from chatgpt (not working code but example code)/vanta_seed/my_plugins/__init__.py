# my_plugins/__init__.py
"""
VANTA Seed → Custom Plugins Package
This file marks 'my_plugins' as a Python package and optionally exposes plugin classes.
"""

# Import plugin modules (optional direct exposure)
from .ollama_plugin import OllamaPlugin
from .deepseek_plugin import DeepSeekPlugin
from .eleven_plugin import ElevenPlugin
from .whisper_plugin import WhisperPlugin

__all__ = [
    "OllamaPlugin",
    "DeepSeekPlugin",
    "ElevenPlugin",
    "WhisperPlugin"
]

print("✅ my_plugins package initialized and plugins loaded.")
