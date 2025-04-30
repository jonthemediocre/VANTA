from models.trinity_node import TrinityNodeMemory # Import the memory model
import logging # Use logging

logger = logging.getLogger(__name__)

class BasicExplorer:
    """A simple Explorer that performs a predefined memory lookup."""
    def explore(self, memory: TrinityNodeMemory):
        """Looks up a specific term in the global memory."""
        query = "recent_drift_pattern" # Example query
        logger.info(f"BasicExplorer: Looking up global memory for '{query}'...")
        
        try:
            results = memory.lookup_global_memory(query=query, search_limit=5)
            if results:
                logger.info(f"BasicExplorer: Found {len(results)} related memory snapshots.")
                # Could process results further, e.g., extract key info
                summary = f"Found {len(results)} snapshots related to '{query}'. First token: {results[0].get('archetype_token', 'N/A')}"
                # Update local memory echo with findings
                memory.update_echo("last_exploration_summary", summary)
                return summary
            else:
                logger.info(f"BasicExplorer: No memory snapshots found for '{query}'.")
                memory.update_echo("last_exploration_summary", f"No results for {query}")
                return f"No results found for {query}"
        except Exception as e:
             logger.error(f"BasicExplorer: Error during memory lookup: {e}", exc_info=True)
             memory.update_echo("last_exploration_error", str(e))
             return f"Error during exploration: {e}" 