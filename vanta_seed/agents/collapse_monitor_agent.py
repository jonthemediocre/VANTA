"""
Collapse Monitor Agent: Observes ritual collapses across the swarm,
identifies patterns, and facilitates self-reflection and consolidation.
"""

import logging
from typing import Dict, Any, Optional, List
from collections import defaultdict # Added for counting
import uuid
import json
from datetime import datetime

from vanta_seed.agents.base_agent import BaseAgent
from vanta_seed.core.models import AgentConfig, TaskData
# from vanta_seed.swarm.orchestration_log import SwarmLogger # Import when needed
from vanta_seed.memory.vector_store import VectorMemoryStore # Added potential import

logger = logging.getLogger(__name__)

# Define status categories for analysis
SUCCESS_STATUSES = ["SUCCESS", "AUDIT_PASSED", "COMPLETED", "RITUAL_ASSIGNED", "COLLAPSE_RECEIVED", "PATTERNS_IDENTIFIED", "COLLAPSE_PROCESSED"] # Add more as needed
FAILURE_STATUSES = ["FAILED", "ERROR", "POLICY_VIOLATION", "UNKNOWN_INTENT"] # Add more as needed

class CollapseMonitorAgent(BaseAgent):
    """Analyzes ritual collapse events to identify patterns and insights."""

    def __init__(self, name: str, config: AgentConfig, logger_instance: logging.Logger, vector_store: Optional[VectorMemoryStore] = None, orchestrator_ref: Optional['VantaMasterCore'] = None):
        """Initializes with optional VectorMemoryStore for persistence."""
        super().__init__(name, config, logger_instance, orchestrator_ref)
        self.logger.info(f"CollapseMonitorAgent '{self._name}' initializing...")
        
        self.vector_store = vector_store # Optional vector store for persistence/querying
        self.collection_name = config.config.get('vector_collection', f"vanta_collapsemonitor_events")
        self.persist_to_vector_store = config.config.get('persist_events', False) and (vector_store is not None)
        
        self.recent_collapses: List[Dict[str, Any]] = [] # In-memory store for recent events
        self.max_history = config.config.get('max_history', 1000) # Max events for in-memory analysis
        self.pattern_threshold = config.config.get('pattern_threshold', 5) # Min occurrences for failure/success patterns
        self.analysis_interval = config.config.get('analysis_interval_seconds', 300) # How often to run analysis
        self._last_analysis_time = 0
        
        if self.persist_to_vector_store:
             logger.info(f"Collapse events will be persisted to vector store collection: '{self.collection_name}'")
        else:
             logger.info(f"Collapse events will be stored in-memory (max_history={self.max_history}).")
             
        self.logger.info(f"CollapseMonitorAgent '{self._name}' initialized.")

    async def perform_task(self, task_data: Dict[str, Any], current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Primary task is processing collapse events.
        """
        intent = task_data.get('intent')
        payload = task_data.get('payload', {})
        self.logger.debug(f"CollapseMonitorAgent '{self.name}' received task/event: {intent}")

        if intent == 'process_ritual_collapse':
            collapse_event = payload
            # Add timestamp if missing
            if 'timestamp' not in collapse_event:
                collapse_event['timestamp'] = datetime.utcnow().isoformat()
                
            self.logger.info(f"Processing collapse event for ritual: {collapse_event.get('ritual_name', 'N/A')} (Task: {collapse_event.get('task_id')})")
            await self._store_collapse_event(collapse_event)
            
            # Optional: Trigger analysis based on time interval
            # current_time = time.time()
            # if current_time - self._last_analysis_time > self.analysis_interval:
            #      patterns = await self._analyze_for_patterns()
            #      if patterns: ... # Handle reporting
            #      self._last_analysis_time = current_time
                 
            # For simplicity, analyze on every event for now, but consider interval
            patterns = await self._analyze_for_patterns()
            if patterns:
                 self.logger.info(f"Identified collapse patterns: {patterns}")
                 # TODO: Report patterns (e.g., message bus, direct call to RL Trainer/Kernel)
                 return {"status": "PATTERNS_IDENTIFIED", "patterns": patterns}
            else:
                 return {"status": "COLLAPSE_PROCESSED"}
        
        elif intent == 'request_pattern_analysis':
            # Allow external trigger for analysis
            self.logger.info("Pattern analysis requested externally.")
            patterns = await self._analyze_for_patterns()
            if patterns:
                return {"status": "PATTERNS_IDENTIFIED", "patterns": patterns}
            else:
                 return {"status": "NO_PATTERNS_FOUND"}

        else:
            self.logger.warning(f"CollapseMonitorAgent received unhandled intent: {intent}")
            return {"status": "UNKNOWN_INTENT"}

    async def _store_collapse_event(self, event: Dict[str, Any]):
        """Stores the collapse event in memory and optionally persists it."""
        # In-memory storage
        self.recent_collapses.append(event)
        if len(self.recent_collapses) > self.max_history:
            self.recent_collapses.pop(0) 
            
        # Persistence to Vector Store
        if self.persist_to_vector_store and self.vector_store:
            try:
                # Generate an ID for the event if not present
                event_id = event.get('event_id', str(uuid.uuid4()))
                event['event_id'] = event_id # Ensure ID is in payload
                
                # --- Embedding Generation (Placeholder) ---
                # TODO: Integrate a real embedding model here for semantic search over events.
                # Using zero vector for now.
                event_vector = None 
                vector_size_for_zero = 384 # Default/placeholder size, MUST match collection
                if event_vector is None:
                    # logger.debug(f"No embedding generated for event {event_id}. Using zero vector.")
                    event_vector = [0.0] * vector_size_for_zero 
                # --- End Embedding Placeholder ---
                                
                # Clean payload for Qdrant (ensure basic types, handle complex objects if needed)
                # Qdrant payload values should be JSON-serializable basic types or lists/dicts thereof.
                # For simplicity, we assume `event` is already suitable.
                qdrant_payload = event.copy() # Use a copy

                point = {
                    "id": event_id,
                    "vector": event_vector, 
                    "payload": qdrant_payload 
                }
                
                # Use await for the async upsert operation
                success = await self.vector_store.upsert_points(self.collection_name, [point])
                if success:
                    logger.debug(f"Successfully persisted collapse event {event_id} to vector store.")
                else:
                     self.logger.warning(f"Failed to persist collapse event {event_id} to vector store (upsert returned False).")
            except Exception as e:
                 self.logger.error(f"Error persisting collapse event {event.get('event_id', 'N/A')} to vector store: {e}", exc_info=True)

    async def _analyze_for_patterns(self) -> List[Dict[str, Any]]:
        """Analyzes recent collapse events for basic success/failure patterns."""
        
        # TODO: Implement querying the vector store for recent events 
        # if self.persist_to_vector_store is True. This would involve:
        # 1. Deciding on a query strategy (last N? time window?)
        # 2. Retrieving points using self.vector_store.query() or similar.
        # 3. Extracting event payloads from the query results.
        # For now, analysis uses only the in-memory self.recent_collapses.
        events_to_analyze = self.recent_collapses 

        if not events_to_analyze:
            return []

        patterns_found = []
        ritual_counts = defaultdict(lambda: {"success": 0, "failure": 0, "total": 0})

        for event in events_to_analyze:
            # Construct a key (can be refined)
            ritual_key = f"{event.get('trinode_name', 'GLOBAL')}:{event.get('ritual_name', 'unknown')}"
            status = event.get('status', 'UNKNOWN').upper()
            
            ritual_counts[ritual_key]["total"] += 1
            if status in SUCCESS_STATUSES:
                ritual_counts[ritual_key]["success"] += 1
            elif status in FAILURE_STATUSES:
                 ritual_counts[ritual_key]["failure"] += 1
            # Else: Ignore intermediate/unknown statuses for this basic analysis

        # Identify patterns based on thresholds
        for key, counts in ritual_counts.items():
            total = counts['total']
            failures = counts['failure']
            successes = counts['success']
            
            if total < self.pattern_threshold: # Skip if not enough data points
                continue 
                
            failure_rate = (failures / total) * 100 if total > 0 else 0
            success_rate = (successes / total) * 100 if total > 0 else 0

            # Pattern: High Failure Rate
            if failures >= self.pattern_threshold and failure_rate > 50.0: # Example threshold
                 patterns_found.append({
                     "type": "high_failure_rate", 
                     "ritual_key": key, 
                     "failure_count": failures,
                     "total_count": total,
                     "failure_rate_percent": round(failure_rate, 2)
                 })
                 self.logger.debug(f"Pattern Found: High failure rate for {key} ({failure_rate:.1f}%)")
                 
            # Pattern: High Success Rate (potentially less actionable, but good to know)
            elif successes >= self.pattern_threshold and success_rate > 95.0: # Example threshold
                 patterns_found.append({
                     "type": "high_success_rate", 
                     "ritual_key": key, 
                     "success_count": successes,
                     "total_count": total,
                     "success_rate_percent": round(success_rate, 2)
                 })
                 self.logger.debug(f"Pattern Found: High success rate for {key} ({success_rate:.1f}%)")

        # TODO: Add more sophisticated pattern detection:
        # - Sequential patterns
        # - Correlation between input parameters and outcomes
        # - Clustering based on event embeddings (if implemented)

        return patterns_found

    async def startup(self):
        await super().startup()
        if self.persist_to_vector_store and self.vector_store:
            try:
                 # Ensure the collection exists
                 # TODO: Determine vector size from an actual embedding model if/when added.
                 vector_size_to_ensure = 384 # Using placeholder size for zero vectors
                 logger.info(f"Ensuring vector collection '{self.collection_name}' exists with size {vector_size_to_ensure} for collapse events...")
                 await self.vector_store.ensure_collection(
                     collection_name=self.collection_name, 
                     vector_size=vector_size_to_ensure, # Must match the zero vector used in _store_collapse_event
                     distance_metric='cosine' # Or another metric if appropriate for future embeddings
                 )
                 logger.info(f"Vector collection '{self.collection_name}' ensured.")
            except Exception as e:
                 self.logger.error(f"Failed to ensure collection '{self.collection_name}' on startup: {e}", exc_info=True)
                 self.persist_to_vector_store = False # Disable persistence if collection fails
                 logger.warning("Disabling vector store persistence for collapse events due to error.")
        self.logger.info(f"CollapseMonitorAgent '{self._name}' specific startup routines complete.")

    async def shutdown(self):
        self.logger.info(f"CollapseMonitorAgent '{self._name}' shutting down...")
        # No specific shutdown needed for in-memory store unless saving state
        await super().shutdown() 