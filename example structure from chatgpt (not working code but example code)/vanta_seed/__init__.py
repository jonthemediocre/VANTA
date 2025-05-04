# === __init__.py ===

"""
VANTA_SEED Initialization
Exposes core and CLI interfaces when imported.
"""

from .core import VantaSeed
from .cli import main as cli_main

__all__ = ["VantaSeed", "cli_main"]
