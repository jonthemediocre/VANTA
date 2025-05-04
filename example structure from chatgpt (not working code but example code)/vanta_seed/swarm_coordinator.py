# === swarm_coordinator.py ===

"""
SwarmCoordinator
Handles coordination of agentic swarms (multi-agent parallel or collaborative tasks).
"""

class SwarmCoordinator:
    def __init__(self, config, plugins):
        self.config = config
        self.plugins = plugins
        self.active_swarms = {}
        print("SwarmCoordinator initialized.")

    def create_swarm(self, swarm_id, agents):
        """
        Register a new swarm with agents.
        """
        self.active_swarms[swarm_id] = {
            "agents": agents,
            "status": "initialized"
        }
        print(f"SwarmCoordinator → Swarm created → ID: {swarm_id} → Agents: {agents}")

    def get_swarm_status(self, swarm_id):
        """
        Retrieve the status of a swarm.
        """
        swarm = self.active_swarms.get(swarm_id)
        if swarm:
            return swarm.get("status", "unknown")
        return "not_found"

    def run_swarm(self, swarm_id):
        """
        Simulate swarm execution.
        """
        swarm = self.active_swarms.get(swarm_id)
        if not swarm:
            print(f"SwarmCoordinator → Swarm '{swarm_id}' not found.")
            return

        print(f"SwarmCoordinator → Running swarm → {swarm_id}")

        for agent in swarm.get("agents", []):
            plugin = self.plugins.get(agent)
            if plugin:
                result = plugin.run()
                print(f"  Agent '{agent}' → {result}")
            else:
                print(f"  Agent '{agent}' → Plugin not found.")

        swarm["status"] = "completed"
        print(f"SwarmCoordinator → Swarm '{swarm_id}' completed.")
