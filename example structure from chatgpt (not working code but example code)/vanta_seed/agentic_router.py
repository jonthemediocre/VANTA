"""
VANTA_SEED Agentic Router
Routes tasks intelligently to solvers, plugins, or sub-agents.
"""

class AgenticRouter:
    def __init__(self, config, kernel):
        self.config = config
        self.kernel = kernel
        self.default_solver = config.get_nested("agentic_router", "default_solver", default="FractalSolver")
        self.routing_rules = config.get_nested("agentic_router", "routing_rules", default=[])
        print("AgenticRouter initialized.")

    def route(self, task_type, task_content):
        print(f"AgenticRouter: Routing task → {task_type}")

        # Routing based on config rules
        for rule in self.routing_rules:
            if rule.get("type") == task_type:
                solver_name = rule.get("solver")
                return self._execute_solver(solver_name, task_content)

            keyword = rule.get("keyword")
            if keyword and keyword in task_content:
                solver_name = rule.get("solver")
                return self._execute_solver(solver_name, task_content)

        # Fallback default solver
        return self._execute_solver(self.default_solver, task_content)

    def _execute_solver(self, solver_name, task_content):
        print(f"AgenticRouter: Executing via solver → {solver_name}")

        if solver_name == "FractalSolver":
            from .fractal_solver import FractalSolver
            solver = FractalSolver()
            return solver.solve(task_content)

        if solver_name == "RetrievalSolver":
            return self.kernel.retrieval.solve(task_content)

        # Try Plugin-based solvers
        plugin = self.kernel.plugins.get_plugin_by_name(solver_name)
        if plugin:
            if hasattr(plugin, "generate"):
                return plugin.generate(task_content)

        return f"AgenticRouter: No valid solver found for {solver_name}"

    def loop(self):
        print("AgenticRouter: Entering event loop (CTRL+C to exit).")
        try:
            while True:
                task_input = input("\n[AgenticRouter] Task → ")
                result = self.route("default", task_input)
                print("\n[AgenticRouter] Result →")
                print(result)
        except KeyboardInterrupt:
            print("\nAgenticRouter: Exiting loop.")
# Agentic router (placeholder)