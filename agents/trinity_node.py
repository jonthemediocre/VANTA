from models.trinity_node import TrinityRole, TrinityNodeState, TrinityNodeMemory
# --- Need Typing for Type Hinting ---
from typing import Optional, Dict, Any, List
# --- Forward reference for MemoryWeave ---
# from vanta_seed.core.memory_weave import MemoryWeave 
# ---------------------------------------

class TrinityNode:
    def __init__(self, node_id: str, global_memory_weave_ref: Optional[Any] = None):
        self.node_id = node_id
        self.state = TrinityNodeState.IDLE
        self.memory = TrinityNodeMemory(global_memory_weave_ref=global_memory_weave_ref)
        # Role assignments store agent instances
        self.roles: Dict[TrinityRole, Optional[Any]] = {
            TrinityRole.EXPLORER: None,
            TrinityRole.EVALUATOR: None,
            TrinityRole.EXECUTOR: None,
        }
        self.parent_node: Optional['TrinityNode'] = None # Type hint for parent
        self.child_nodes: list['TrinityNode'] = [] # Type hint for children

    def assign_role(self, role: TrinityRole, agent):
        """Assigns an agent instance to a specific role."""
        if role not in self.roles:
            print(f"Error: Invalid role {role} specified.") # Basic error handling
            return
        self.roles[role] = agent
        print(f"Assigned agent {type(agent).__name__} to role {role.value} for node {self.node_id}")

    # --- NEW: Spawn Child Method ---
    def spawn_child(self, child_node_id: Optional[str] = None) -> 'TrinityNode':
        """Creates a new TrinityNode and adds it as a child of this node."""
        import uuid # Local import for ID generation
        if not child_node_id:
            child_node_id = f"{self.node_id}_child_{uuid.uuid4().hex[:4]}"
            
        print(f"Node '{self.node_id}' spawning child: {child_node_id}") # Simple logging
        child_node = TrinityNode(child_node_id, global_memory_weave_ref=self.memory.global_memory)
        
        # Optionally assign default roles or inherit/mutate from parent
        # For now, let's assign the basic roles if available globally or via imports
        # This assumes BasicExplorer, etc., are accessible here
        try:
             # Corrected import path assuming roles are in a subfolder
             from .roles.basic_explorer import BasicExplorer
             from .roles.basic_evaluator import BasicEvaluator
             from .roles.basic_executor import BasicExecutor
             child_node.assign_role(TrinityRole.EXPLORER, BasicExplorer())
             child_node.assign_role(TrinityRole.EVALUATOR, BasicEvaluator())
             child_node.assign_role(TrinityRole.EXECUTOR, BasicExecutor())
        except ImportError as e:
             print(f"Warning: Could not import basic roles for child node {child_node_id}. Error: {e}")
             
        self.add_child_node(child_node)
        return child_node
    # -----------------------------

    def add_child_node(self, node: 'TrinityNode'):
        """Registers another TrinityNode as a child of this one."""
        if node not in self.child_nodes:
            node.parent_node = self
            self.child_nodes.append(node)
            print(f"Added node {node.node_id} as child of {self.node_id}")

    def breath_cycle(self):
        """Executes one cycle of Explore -> Evaluate -> Execute, 
           then recursively triggers breath cycles for children."""
        print(f"--- Node {self.node_id}: Starting Breath Cycle --- (State: {self.state.value})")
        if self.state != TrinityNodeState.IDLE:
            print(f"Warning: Node {self.node_id} already in state {self.state.value}. Skipping breath cycle.")
            return None
            
        self.state = TrinityNodeState.BREATHING
        exploration_result = None
        decision = None
        execution_result = None
        
        # 1. Explore
        explorer_agent = self.roles.get(TrinityRole.EXPLORER)
        if explorer_agent and hasattr(explorer_agent, 'explore'):
            try:
                print(f"  Role: {TrinityRole.EXPLORER.value} exploring...")
                exploration_result = explorer_agent.explore(self.memory)
                print(f"  Explorer Result: {exploration_result}")
                # TODO: Update memory with exploration results
            except Exception as e:
                 print(f"  Error during Exploration: {e}")
        else:
             print(f"  No valid Explorer assigned or method missing.")

        # 2. Evaluate
        evaluator_agent = self.roles.get(TrinityRole.EVALUATOR)
        if evaluator_agent and hasattr(evaluator_agent, 'evaluate'):
             try:
                print(f"  Role: {TrinityRole.EVALUATOR.value} evaluating...")
                # Pass exploration result to evaluator?
                decision = evaluator_agent.evaluate(self.memory, exploration_result)
                print(f"  Evaluator Decision: {decision}")
                # TODO: Update memory with evaluation decision
             except Exception as e:
                 print(f"  Error during Evaluation: {e}")
        else:
             print(f"  No valid Evaluator assigned or method missing.")

        # 3. Execute
        executor_agent = self.roles.get(TrinityRole.EXECUTOR)
        if executor_agent and hasattr(executor_agent, 'execute'):
            try:
                print(f"  Role: {TrinityRole.EXECUTOR.value} executing based on decision: {decision}...")
                # Pass decision to executor?
                execution_result = executor_agent.execute(self.memory, decision)
                print(f"  Executor Result: {execution_result}")
                # TODO: Update memory with execution results (echoes)
            except Exception as e:
                 print(f"  Error during Execution: {e}")
        else:
             print(f"  No valid Executor assigned or method missing.")

        print(f"--- Node {self.node_id}: Breath Cycle Complete --- Recursively breathing children...")
        # --- Recursive Breath Call --- 
        child_results = []
        if self.child_nodes:
             print(f"  Node {self.node_id} triggering breath for {len(self.child_nodes)} children...")
             for child in self.child_nodes:
                  # Simple sequential execution for now. Could be parallelized with asyncio.gather
                  try:
                      child_result = child.breath_cycle() # Recursive call
                      child_results.append({child.node_id: child_result})
                  except Exception as e:
                       print(f"  Error during child ({child.node_id}) breath cycle: {e}")
                       child_results.append({child.node_id: {"error": str(e)}})
             print(f"  Node {self.node_id}: Children breath cycles finished.")
        # ---------------------------
        
        self.state = TrinityNodeState.IDLE
        # Return combined results? Or just rely on memory updates?
        # Include child results for potential aggregation/analysis by parent/Queen
        return {
             "node_id": self.node_id,
             "exploration": exploration_result, 
             "decision": decision, 
             "execution": execution_result,
             "child_results": child_results
        }

    def mutate(self, base_mutation_rate: float = 0.05, performance_factor: float = 0.5):
        """Potentially mutates the node by spawning a child, guided by performance.
        
        Args:
            base_mutation_rate: The minimum probability (0.0 to 1.0) of spawning.
            performance_factor: How much performance affects spawn rate (0.0 = no effect).
        """
        print(f"--- Node {self.node_id}: Considering Mutation... ---")
        self.state = TrinityNodeState.MUTATING
        mutated = False
        
        # --- Performance-Guided Spawning --- 
        import random # Needed for probability check
        
        # TODO: Retrieve actual performance metric (0.0 low success -> 1.0 high success)
        #       from self.memory.echoes (e.g., set by Evaluator)
        recent_success_rate = self.memory.get_echo("recent_success_rate") 
        if recent_success_rate is None:
            print(f"  Warning: recent_success_rate not found in memory echoes. Defaulting to 0.5 for mutation calculation.")
            recent_success_rate = 0.5 # Default to neutral if not found
            
        # Ensure metric is within bounds
        recent_success_rate = max(0.0, min(1.0, recent_success_rate)) 

        # Calculate spawn probability: Higher probability if success rate is low
        spawn_probability = base_mutation_rate + performance_factor * (1.0 - recent_success_rate)
        # Clamp probability between 0.0 and 1.0 (or a reasonable max, e.g., 0.9)
        spawn_probability = max(0.0, min(1.0, spawn_probability)) 

        print(f"  Calculated Spawn Probability: {spawn_probability:.2f} (Base: {base_mutation_rate}, PerfFactor: {performance_factor}, SuccessRate: {recent_success_rate:.2f})")

        if random.random() < spawn_probability:
            print(f"  Mutation Triggered: Spawning child")
            try:
                self.spawn_child() # Call the existing spawn method
                mutated = True
            except Exception as e:
                print(f"  Error during spawn mutation: {e}")
        else:
             print(f"  No mutation this cycle.")
        # ------------------------------------
        
        # TODO: Implement other mutation types (pruning, role swap, memory adjustment)
        
        print(f"--- Node {self.node_id}: Mutation Phase Complete (Mutated: {mutated}) ---")
        self.state = TrinityNodeState.IDLE
        return mutated # Return whether a mutation occurred

    def collapse(self, child_breath_results: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Collapses the node's state and children's results into a summary.
        
        Args:
            child_breath_results: Optional list of results from children's breath cycles.
            
        Returns:
            A dictionary summarizing the collapsed state.
        """
        print(f"--- Node {self.node_id}: Collapsing State... ---")
        self.state = TrinityNodeState.COLLAPSING
        
        # 1. Gather key info from local memory echoes
        last_decision = self.memory.get_echo("last_evaluation_decision")
        last_execution_token = self.memory.get_echo("last_execution_token")
        last_exploration = self.memory.get_echo("last_exploration_summary")
        # Add other relevant echoes...
        
        # 2. Process results from children (if provided)
        children_summary = []
        if child_breath_results:
            print(f"  Collapsing results from {len(child_breath_results)} children...")
            for child_result in child_breath_results:
                 # Extract key info from each child result dictionary
                 # The structure depends on what `breath_cycle` returns
                 child_id = list(child_result.keys())[0] # Assumes {child_id: result_dict}
                 child_data = child_result.get(child_id, {})
                 children_summary.append({
                      "child_id": child_id,
                      "decision": child_data.get("decision"),
                      "execution_token": child_data.get("execution", {}).get("last_execution_token"), # Example nesting
                      "error": child_data.get("error") 
                 })
                 
        # 3. Formulate the collapsed summary
        collapsed_state = {
            "node_id": self.node_id,
            "status": "collapsed",
            "local_summary": {
                "last_decision": last_decision,
                "last_execution_token": last_execution_token,
                "last_exploration": last_exploration
            },
            "children_summary": children_summary,
            "child_count": len(self.child_nodes) # Include current child count
            # TODO: Add other relevant metrics (e.g., aggregated drift, resource usage)
        }
        
        print(f"--- Node {self.node_id}: Collapse Complete --- Summary:
{collapsed_state}
")
        self.state = TrinityNodeState.IDLE # Return to idle after collapse
        return collapsed_state

    # --- Optional: Representation for easier debugging ---
    def __repr__(self) -> str:
         return f"TrinityNode(id='{self.node_id}', state='{self.state.value}', children={len(self.child_nodes)})"
    # ---------------------------------------------------- 