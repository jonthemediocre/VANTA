"""
Agent responsible for AI-powered master data management, deduplication,
and exposing unified entities.
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from vanta_seed.agents.base_agent import BaseAgent # Use absolute import
from vanta_seed.core.models import AgentConfig, TaskData
from vanta_seed.memory.vector_store import VectorMemoryStore, QdrantVectorStore # Added
# Import core models if needed later
# from vanta_seed.core.data_models import AgentInput, AgentResponse, AgentMessage
import numpy as np # For clamping
from sentence_transformers import SentenceTransformer # For embeddings
# from sklearn.metrics.pairwise import cosine_similarity # Alt similarity calc if needed
import uuid
from datetime import datetime

# Define result status constants
RESULT_SUCCESS = "SUCCESS" # Entity resolved (merged or correctly skipped/saved)
RESULT_PARTIAL = "PARTIAL" # New entity created (no match found)
RESULT_FAIL = "FAIL"       # Action attempted but criteria not met (e.g., low similarity on merge attempt)
RESULT_ERROR = "ERROR"     # Internal agent error during processing

# --- Get Logger ---
# Use the base agent's logger retrieval or a dedicated one
logger = logging.getLogger(__name__)

class DataUnifierAgent(BaseAgent):
    """
    Handles ingestion, ML-driven deduplication & merge, and exposing entities.
    Uses a persistent VectorMemoryStore (Qdrant).
    Optimized for Ritual RL with expanded actions and feedback.
    """

    def __init__(self, name: str, config: AgentConfig, logger_instance: logging.Logger, vector_store: VectorMemoryStore, orchestrator_ref: Optional['VantaMasterCore'] = None):
        """Initializes the Data Unifier Agent with a VectorMemoryStore."""
        super().__init__(name, config, logger_instance, orchestrator_ref)
        self.logger.info(f"Ritual RL Optimized DataUnifierAgent '{self._name}' initializing...")
        
        # Configuration
        agent_specific_config = getattr(config, 'config', {})
        self.embedding_model_name = agent_specific_config.get('embedding_model', 'all-MiniLM-L6-v2')
        self.base_deduplication_threshold = agent_specific_config.get("deduplication_threshold", 0.75) 
        self.threshold_step = agent_specific_config.get("threshold_step", 0.05) # Step for RL actions 2 & 3
        self.merge_strategy = agent_specific_config.get("merge_strategy", "recency") 
        self.fields_to_embed = agent_specific_config.get("fields_to_embed", ["name", "description"]) 
        self.collection_name = agent_specific_config.get("vector_collection", f"vanta_{name.lower()}_entities") # Configurable collection name

        self.embedding_model: Optional[SentenceTransformer] = None
        self.vector_store = vector_store # Injected vector store instance
        self.vector_size: Optional[int] = None # Determined after model loading

        self.logger.info(f"Config - Embedding Model: {self.embedding_model_name}")
        self.logger.info(f"Config - Base Threshold: {self.base_deduplication_threshold}")
        self.logger.info(f"Config - Fields to Embed: {self.fields_to_embed}")
        self.logger.info(f"Config - Vector Collection: {self.collection_name}")
        self.logger.info(f"DataUnifierAgent '{self._name}' initialized.")

    async def execute(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main execution loop override. Delegates core logic to perform_task
        after handling standard BaseAgent state updates and context processing.
        """
        self.logger.debug(f"DataUnifierAgent '{self._name}' executing task: {task_data.get('intent')}")
        # BaseAgent.execute handles state updates, context processing, and calling perform_task
        result_package = await super().execute(task_data)
        self.logger.debug(f"DataUnifierAgent '{self._name}' execution finished.")
        return result_package

    async def perform_task(self, task_data: Dict[str, Any], current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Core logic for data unification tasks based on input data.

        Expected task_data format:
        {
            "task_type": "unify_records" | "query_entity",
            "payload": {
                "raw_records": [...] // for unify_records
                "entity_id": "..." // for query_entity
                // other params
            }
        }
        """
        intent = task_data.get('intent')
        payload = task_data.get('payload', {})
        self.logger.info(f"DataUnifier '{self.name}' performing task: {intent}, Action: {payload.get('action_taken')}")

        if self.vector_store is None or self.embedding_model is None:
             self.logger.error("Agent prerequisites not met: Vector Store or Embedding Model not initialized.")
             return {"status": RESULT_ERROR, "message": "Agent not fully initialized", "similarity": 0.0, "action_taken": payload.get("action_taken", -1)}

        if intent == 'deduplication_step': # Task driven by Gym Env
            # This expects a single record for processing in the payload
            record_data = payload.get("record")
            action_taken = payload.get("action_taken")
            if record_data is None or action_taken is None:
                self.logger.error("Missing 'record' or 'action_taken' in deduplication_step payload")
                return {"status": RESULT_ERROR, "message": "Invalid payload for deduplication step", "similarity": 0.0, "action_taken": action_taken or -1}
            
            try:
                # The core logic now includes handling the RL action
                dedup_result = await self.handle_deduplication_action(record_data, action_taken)
                # Return the structured result protocol
                return dedup_result 
            except Exception as e:
                self.logger.error(f"Error during handle_deduplication_action: {e}", exc_info=True)
                return {"status": RESULT_ERROR, "message": str(e), "similarity": 0.0, "action_taken": action_taken}

        elif intent == 'get_unified_entity': # Direct query (e.g., from API)
             entity_id = payload.get('entity_id')
             entity_data = await self.get_entity_by_id(entity_id) # Changed to await
             if entity_data:
                 # Return just the payload (unified data and metadata)
                 return {"status": RESULT_SUCCESS, "data": entity_data} 
             else:
                 return {"status": RESULT_FAIL, "message": f"Entity {entity_id} not found"}
        
        # Handle other intents if needed...
        else:
            self.logger.warning(f"Unknown intent received: {intent}")
            return {"status": RESULT_ERROR, "message": f"Unknown intent: {intent}", "similarity": 0.0, "action_taken": -1}

    async def receive_message(self, message: 'AgentMessage'):
        """Handles incoming messages from the message bus."""
        self.logger.info(f"DataUnifierAgent '{self.name}' received message from {message.sender_agent}: {message.intent}")
        # TODO: Implement message handling logic if needed
        pass

    async def startup(self):
        """Load embedding model and initialize vector store on startup."""
        await super().startup()
        self.logger.info(f"DataUnifierAgent '{self._name}' starting up specific routines...")
        
        # 1. Load Embedding Model
        try:
            self.logger.info(f"Loading sentence transformer model: {self.embedding_model_name}")
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            # Determine vector size from the loaded model
            # Use a dummy encode to get the size
            self.vector_size = self.embedding_model.get_sentence_embedding_dimension()
            if not self.vector_size:
                 # Fallback if above fails
                 dummy_embedding = self.embedding_model.encode("test")
                 self.vector_size = dummy_embedding.shape[0]
            self.logger.info(f"Sentence transformer model loaded successfully. Vector size: {self.vector_size}")
        except Exception as e:
            self.logger.error(f"Failed to load embedding model '{self.embedding_model_name}': {e}", exc_info=True)
            self.embedding_model = None 
            self.vector_size = None
            # Optional: Prevent agent from fully starting if model load fails?
            # raise RuntimeError("Failed to load embedding model") from e
        
        # 2. Initialize Vector Store
        if self.vector_store:
            try:
                await self.vector_store.initialize()
                self.logger.info("Vector store initialized.")
                 # 3. Ensure Collection Exists (only if model loaded)
                if self.vector_size:
                    self.logger.info(f"Ensuring vector collection '{self.collection_name}' exists with size {self.vector_size}...")
                    await self.vector_store.ensure_collection(
                        collection_name=self.collection_name,
                        vector_size=self.vector_size,
                        distance_metric='cosine' # Or make configurable
                    )
                    self.logger.info(f"Vector collection '{self.collection_name}' ensured.")
                else:
                     self.logger.warning("Skipping collection check as vector size could not be determined.")
            except Exception as e:
                 self.logger.error(f"Failed to initialize vector store or ensure collection: {e}", exc_info=True)
                 # Decide if this is critical - maybe allow running without vector store?
                 # self.vector_store = None # Or handle gracefully later
                 # raise RuntimeError("Failed to initialize vector store") from e
        else:
             self.logger.warning("No vector store provided to DataUnifierAgent.")

        self.logger.info(f"DataUnifierAgent '{self._name}' startup complete.")

    async def handle_deduplication_action(self, record_data: Dict[str, Any], action: int) -> Dict[str, Any]:
        """Processes a record based on the RL-chosen action using the vector store."""
        if self.embedding_model is None or self.vector_store is None or self.vector_size is None:
            return {"status": RESULT_ERROR, "message": "Agent not fully initialized (model/store/size missing)", "similarity": 0.0, "action_taken": action}

        # 1. Generate Text and Embedding for incoming record
        text_to_embed = " ".join([str(record_data.get(f, "")) for f in self.fields_to_embed])
        if not text_to_embed.strip():
            logger.warning("No text content found in record to generate embedding.")
            if action == 5: # If forced save new, allow it
                 new_id = await self._save_new_entity(record_data, None) # Await async save
                 if new_id:
                    return {"status": RESULT_SUCCESS, "message": f"Forced save new entity {new_id} (no embeddable text)", "similarity": 0.0, "action_taken": action, "entity_id": new_id}
                 else:
                    return {"status": RESULT_ERROR, "message": "Failed to save new entity (no embeddable text)", "similarity": 0.0, "action_taken": action}
            else:
                 return {"status": RESULT_FAIL, "message": "No embeddable text in record", "similarity": 0.0, "action_taken": action}
        
        try:
            incoming_embedding = self.embedding_model.encode(text_to_embed)
        except Exception as e:
            logger.error(f"Embedding failed: {e}", exc_info=True)
            return {"status": RESULT_ERROR, "message": f"Embedding generation failed: {e}", "similarity": 0.0, "action_taken": action}

        # Handle Action 0: Skip deduplication
        if action == 0:
            logger.debug(f"Action 0: Skipping deduplication for record.")
            return {"status": RESULT_SUCCESS, "message": "Skipped deduplication as requested", "similarity": 0.0, "action_taken": action}

        # Find best existing match using vector store
        best_match_id, best_similarity = await self._find_best_match(incoming_embedding) # Await async query

        # Handle Action 5: Force Save New Entity
        if action == 5:
            logger.debug(f"Action 5: Forcing save new entity.")
            new_id = await self._save_new_entity(record_data, incoming_embedding) # Await async save
            if new_id:
                return {"status": RESULT_SUCCESS, "message": f"Forced save new entity {new_id}", "similarity": best_similarity, "action_taken": action, "entity_id": new_id}
            else:
                return {"status": RESULT_ERROR, "message": "Failed to force save new entity", "similarity": best_similarity, "action_taken": action}

        # Determine Threshold based on Actions 1, 2, 3
        threshold_modifier = {1: 0.0, 2: -self.threshold_step, 3: self.threshold_step}.get(action, 0.0)
        effective_threshold = np.clip(self.base_deduplication_threshold + threshold_modifier, 0.0, 1.0)
        logger.debug(f"Action {action}: Effective Threshold = {effective_threshold:.3f}, Best Similarity = {best_similarity:.4f}")

        is_match = best_similarity >= effective_threshold

        # Handle Action 4: Force Merge
        if action == 4:
            if best_match_id:
                logger.debug(f"Action 4: Forcing merge with entity {best_match_id} (Similarity: {best_similarity:.4f})")
                merged = await self._merge_into_existing(best_match_id, record_data) # Await async merge
                if merged:
                    return {"status": RESULT_SUCCESS, "message": f"Forced merge with {best_match_id}", "similarity": best_similarity, "action_taken": action, "entity_id": best_match_id}
                else:
                     return {"status": RESULT_ERROR, "message": f"Failed to force merge with {best_match_id}", "similarity": best_similarity, "action_taken": action}
            else:
                logger.warning(f"Action 4: Force merge requested, but no existing entity found to merge with.")
                return {"status": RESULT_FAIL, "message": "Force merge failed: no entity found", "similarity": best_similarity, "action_taken": action}

        # Handle Actions 1, 2, 3 (Standard Dedupe with potentially adjusted threshold)
        if is_match and best_match_id:
            logger.debug(f"Action {action}: Found match >= threshold. Merging with {best_match_id}.")
            merged = await self._merge_into_existing(best_match_id, record_data) # Await async merge
            if merged:
                return {"status": RESULT_SUCCESS, "message": f"Merged with {best_match_id}", "similarity": best_similarity, "action_taken": action, "entity_id": best_match_id}
            else:
                 return {"status": RESULT_ERROR, "message": f"Failed merge with {best_match_id}", "similarity": best_similarity, "action_taken": action}

        else: # No match above threshold
            logger.debug(f"Action {action}: No match found >= threshold {effective_threshold:.3f}. Creating new entity.")
            new_id = await self._save_new_entity(record_data, incoming_embedding) # Await async save
            if new_id:
                return {"status": RESULT_PARTIAL, "message": f"No match found, created new entity {new_id}", "similarity": best_similarity, "action_taken": action, "entity_id": new_id}
            else:
                return {"status": RESULT_ERROR, "message": "Failed to create new entity after no match", "similarity": best_similarity, "action_taken": action}

    async def _find_best_match(self, incoming_embedding: np.ndarray) -> Tuple[Optional[str], float]:
        """Finds the existing entity with the highest embedding similarity using the vector store."""
        if self.vector_store is None or incoming_embedding is None:
            return None, 0.0

        try:
            # Query the vector store
            search_results = await self.vector_store.query(
                collection_name=self.collection_name,
                query_vector=incoming_embedding,
                limit=1, # We only need the top match
                with_payload=False, # Don't need payload for this check
                with_vector=False,
                # Optional: Use score_threshold slightly lower than base threshold?
                # score_threshold=self.base_deduplication_threshold - 0.1 
            )

            if search_results:
                best_match = search_results[0]
                # Ensure ID is retrieved correctly (Qdrant returns string or int based on what was stored)
                best_match_id = str(best_match['id']) 
                best_similarity = float(best_match['score'])
                logger.debug(f"Vector store query found best match: ID={best_match_id}, Score={best_similarity:.4f}")
                return best_match_id, best_similarity
            else:
                logger.debug("Vector store query found no matches.")
                return None, 0.0

        except Exception as e:
            logger.error(f"Error querying vector store in _find_best_match: {e}", exc_info=True)
            return None, 0.0

    async def _save_new_entity(self, record_data: Dict[str, Any], embedding: Optional[np.ndarray]) -> Optional[str]:
        """Saves a new entity to the vector store."""
        if self.vector_store is None:
            logger.error("Cannot save entity: Vector store not available.")
            return None
            
        # Qdrant IDs can be UUIDs or integers. Using string UUIDs is generally safer.
        new_id = str(uuid.uuid4()) 
        
        # Payload includes the unified data and metadata
        payload = {
            "unified_data": record_data.copy(), # Store a copy of the first record's data
            "sources": [record_data.get('source', 'unknown')], # Track sources
            "created_ts": datetime.utcnow().isoformat(),
            "updated_ts": datetime.utcnow().isoformat(),
            "version": 1
        }
        
        # Prepare point for upsert
        point_to_upsert = {
            "id": new_id,
            "vector": embedding.tolist() if embedding is not None else [], # Convert numpy array to list for JSON serialization if needed by client
            "payload": payload
        }
        
        # Handle case with no embedding - Qdrant requires vector of correct dimension
        if embedding is None:
            logger.warning(f"Saving new entity {new_id} without an embedding. Using zero vector.")
            if self.vector_size is None:
                logger.error(f"Cannot create zero vector for entity {new_id}: vector size unknown.")
                return None
            point_to_upsert["vector"] = [0.0] * self.vector_size # Use zero vector

        try:
            success = await self.vector_store.upsert_points(
                collection_name=self.collection_name,
                points=[point_to_upsert]
            )
            if success:
                logger.info(f"Saved new entity {new_id} to vector store.")
                return new_id
            else:
                logger.error(f"Failed to upsert new entity {new_id} into vector store.")
                return None
        except Exception as e:
            logger.error(f"Error saving new entity {new_id} to vector store: {e}", exc_info=True)
            return None

    async def _merge_into_existing(self, existing_id: str, new_record_data: Dict[str, Any]) -> bool:
        """Merges new record data into an existing entity in the vector store."""
        if self.vector_store is None:
            logger.error("Cannot merge entity: Vector store not available.")
            return False

        try:
            # 1. Retrieve the existing point
            existing_point = await self.vector_store.get_point(self.collection_name, existing_id)
            if not existing_point:
                self.logger.error(f"Attempted to merge into non-existent entity ID in vector store: {existing_id}")
                return False

            existing_payload = existing_point.get("payload", {})
            existing_unified_data = existing_payload.get("unified_data", {})
            existing_vector = existing_point.get("vector") # Keep the original vector

            self.logger.debug(f"Merging data into existing entity {existing_id}. Strategy: {self.merge_strategy}")

            # 2. Perform merge logic on the payload
            merged_data = existing_unified_data.copy()
            updated = False

            # Apply Merge Strategy 
            if self.merge_strategy == "recency":
                for key, new_value in new_record_data.items():
                    if key in ["id", "source"] or new_value is None or new_value == "": continue
                    existing_value = merged_data.get(key)
                    if existing_value != new_value:
                        merged_data[key] = new_value
                        self.logger.debug(f"  - Updated field '{key}' based on recency.")
                        updated = True
            else: # Fallback/Other strategies
                self.logger.warning(f"Merge strategy '{self.merge_strategy}' not implemented. Defaulting to simple update.")
                for key, new_value in new_record_data.items():
                    if key in ["id", "source"] or new_value is None or new_value == "": continue
                    if merged_data.get(key) != new_value:
                         merged_data[key] = new_value
                         updated = True

            # Update Metadata in payload
            new_source = new_record_data.get('source', 'unknown')
            current_sources = existing_payload.get('sources', [])
            if new_source not in current_sources:
                # Ensure sources is treated as a list
                if not isinstance(current_sources, list):
                    current_sources = [current_sources] if current_sources else []
                current_sources.append(new_source)
                existing_payload['sources'] = current_sources # Update the list in the payload
                self.logger.debug(f"  - Added source: {new_source}")
                updated = True

            # 3. If updated, upsert the modified point (using the original vector)
            if updated:
                existing_payload["unified_data"] = merged_data
                existing_payload["updated_ts"] = datetime.utcnow().isoformat()
                existing_payload["version"] = existing_payload.get("version", 0) + 1
                
                # Ensure vector is a list for upsert if it came back as numpy array
                if existing_vector is not None and isinstance(existing_vector, np.ndarray):
                     upsert_vector = existing_vector.tolist()
                elif existing_vector is None: # Handle missing vector case - use zero vector?
                    logger.warning(f"Merging entity {existing_id} which has no vector. Using zero vector for upsert.")
                    if self.vector_size is None: raise ValueError("Cannot use zero vector: vector size unknown.")
                    upsert_vector = [0.0] * self.vector_size
                else:
                    upsert_vector = existing_vector # Assume it's already a list

                point_to_upsert = {
                    "id": existing_id,
                    "vector": upsert_vector, 
                    "payload": existing_payload # Upsert the whole modified payload
                }
                
                success = await self.vector_store.upsert_points(
                    collection_name=self.collection_name,
                    points=[point_to_upsert]
                )
                if success:
                    self.logger.info(f"Successfully merged data into entity {existing_id}. New version: {existing_payload['version']}")
                    return True
                else:
                    self.logger.error(f"Failed to upsert merged entity {existing_id} into vector store.")
                    return False
            else:
                self.logger.debug(f"No changes made during merge for entity {existing_id}. No upsert needed.")
                return True # Merge technically succeeded as no changes were needed

        except Exception as e:
             logger.error(f"Error merging entity {existing_id}: {e}", exc_info=True)
             return False

    async def get_entity_by_id(self, entity_id: Optional[str]) -> Optional[Dict[str, Any]]:
         """Retrieves a unified entity's payload by its ID from the vector store."""
         if not entity_id or self.vector_store is None:
             return None
         
         try:
             point_data = await self.vector_store.get_point(self.collection_name, entity_id)
             if point_data:
                 # Return only the payload, which contains unified_data and metadata
                 return point_data.get("payload") 
             else:
                 return None
         except Exception as e:
             logger.error(f"Error retrieving entity {entity_id} from vector store: {e}", exc_info=True)
             return None

    async def shutdown(self):
        """Custom shutdown logic including vector store shutdown."""
        self.logger.info(f"DataUnifierAgent '{self._name}' shutting down specific routines...")
        if self.vector_store:
            try:
                await self.vector_store.shutdown()
                self.logger.info("Vector store shut down successfully.")
            except Exception as e:
                self.logger.error(f"Error shutting down vector store: {e}", exc_info=True)
        # TODO: Release other resources, save state
        await super().shutdown() # Call base shutdown if needed

# Example of how this agent might be instantiated and used (for testing/dev)
if __name__ == '__main__':
    import asyncio
    from vanta_seed.core.models import AgentConfig # Import needed class
    from vanta_seed.memory.vector_store import QdrantVectorStore # Import needed class
    
    # Basic logging setup for the example
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    main_logger = logging.getLogger(__name__)

    async def run_agent_startup_test():
        main_logger.info("--- Starting DataUnifierAgent Startup Test ---")
        # Setup Vector Store (assuming Qdrant running locally on default ports)
        qdrant_store = QdrantVectorStore(host="localhost", port=6333)
        
        # Mock config (ensure collection name matches default or is set)
        mock_config_data = {"config": {"vector_collection": "vanta_dataunifieragent_entities"}} # Use agent's default name logic
        # Use Pydantic model for AgentConfig
        mock_agent_config = AgentConfig(
             name="TestDUA", 
             class_path="vanta_seed.agents.data_unifier_agent.DataUnifierAgent", # Example path
             config=mock_config_data.get('config',{}), # Pass the inner config dict
             enabled=True
        )

        agent = None # Define agent outside try block for finally
        try:
            # Instantiate Agent
            main_logger.info("Instantiating DataUnifierAgent...")
            agent = DataUnifierAgent(name="TestDUA", config=mock_agent_config, logger_instance=main_logger, vector_store=qdrant_store)
            
            main_logger.info("Calling agent.startup()...")
            await agent.startup() # This initializes vector store and ensures collection
            main_logger.info("Agent startup successful!")

            # --- Optional: Add a simple test interaction ---
            # Example: Save a dummy entity
            # test_record = {"id": "test-001", "name": "Test Record", "description": "A dummy record for testing."}
            # test_embedding = agent.embedding_model.encode(test_record["description"])
            # save_result = await agent._save_new_entity(test_record, test_embedding)
            # main_logger.info(f"Save new entity result: {save_result}")
            # --- End Optional Interaction ---

        except Exception as e:
             main_logger.error(f"An error occurred during the test: {e}", exc_info=True)
        finally:
            if agent:
                 main_logger.info("Calling agent.shutdown()...")
                 await agent.shutdown()
                 main_logger.info("Agent shutdown complete.")
            main_logger.info("--- DataUnifierAgent Startup Test Finished ---")

    # Run the async function
    asyncio.run(run_agent_startup_test()) 