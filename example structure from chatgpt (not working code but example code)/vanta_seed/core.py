"""
VANTA_SEED Core Kernel
Handles initialization and main loop for all modules.
"""

import os
from .config import Config
from .memory_store import MemoryStore
from .episodic_memory import EpisodicMemory
from .identity import Identity
from .collapse import Collapse
from .governance_engine import GovernanceEngine
from .procedural_engine import ProceduralEngine
from .automutator import Automutator
from .autonomous_tasker import AutonomousTasker
from .ritual_executor import RitualExecutor
from .agentic_router import AgenticRouter
from .plugins import PluginManager
from .lora_manager import LoRAManager
from .retrieval_solver import RetrievalSolver
from .audit_logger import AuditLogger

class VantaSeed:
    def __init__(self, config_path="templates/config.yaml"):
        print("VantaSeed Kernel initializing...")
        self.config = Config(config_path)

        # Load Core Components
        self.plugins = PluginManager(self.config)
        self.memory = MemoryStore(self.config)
        self.episodic = EpisodicMemory(self.config, self.memory)
        self.identity = Identity(self.config.get('identity_file'))
        self.collapse = Collapse(self.config.get('collapse_file'))
        self.governance = GovernanceEngine(self.config)
        self.procedural = ProceduralEngine(self.config)
        self.automutator = Automutator(self.config, self.procedural, self.governance)
        self.autonomous = AutonomousTasker(self.config, self.automutator)
        self.rituals = RitualExecutor(self.config, self)
        self.router = AgenticRouter(self.config, self)

        self.retrieval = RetrievalSolver(self.config, self.memory, self.episodic, self.plugins)
        self.audit = AuditLogger(self.config)

        self.identity.load()
        self.collapse.load()
        self.governance.load_rules()
        self.procedural.load_rules()

        print("VantaSeed Kernel ready.")

    def start(self):
        print("Starting VantaSeed...")
        self.autonomous.start()
        self.rituals.start()
        self.router.loop()

    def shutdown(self):
        print("Shutting down VantaSeed...")
        self.autonomous.shutdown()
        self.rituals.shutdown()
# Core orchestrator (placeholder)