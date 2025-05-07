import sys
import os # Keep os import here as it's used by os._exit later if uncommented
print("--- DEBUG: Current sys.path START ---")
for p_item in sys.path: # Changed variable name to avoid clash if 'p' is used later
    print(p_item)
print("--- DEBUG: Current sys.path END ---")
print("\n--- DEBUG: Effective path for 'vanta_seed.exceptions' START ---")
try:
    import vanta_seed.exceptions
    print(vanta_seed.exceptions.__file__)
except ImportError as e:
    print(f"Could not import vanta_seed.exceptions: {e}")
print("--- DEBUG: Effective path for 'vanta_seed.exceptions' END ---")
print("\n--- DEBUG: Attempting main script imports now... ---\n")
# Optional: uncomment next line to ONLY run this debug block and then exit
# import os; os._exit(1) 

import logging
from typing import List, Tuple, Optional, Dict, Any, Union
from collections import Counter

# Assuming DataCatalogService will be used to fetch candidates and store results
from vanta_seed.services.data_catalog_service import DataCatalogService, KnowledgeData, OperationalData
from vanta_seed.schemas.mythic_schemas import MythicObject, MythicLink
# Potentially custom exceptions for this service
from vanta_seed.exceptions import DataCatalogException, OperationFailure, StorageFailure

logger = logging.getLogger(__name__)

DEFAULT_FREQUENCY_THRESHOLD = 3 # Default number of occurrences to trigger a collapse

class RitualCollapseService:
    """
    Service responsible for identifying patterns in existing data (KnowledgeData, OperationalData)
    and collapsing them into more abstract MythicObjects and MythicLinks.
    """

    def __init__(self, data_catalog_service: DataCatalogService):
        if not data_catalog_service:
            logger.error("RitualCollapseService initialized with a null DataCatalogService.")
            raise ValueError("DataCatalogService cannot be None for RitualCollapseService.")
        self.catalog_service = data_catalog_service
        logger.info("RitualCollapseService initialized.")

    def identify_collapse_candidates(self, 
                                     data_type: str = "knowledge", 
                                     pattern_config: Optional[Dict[str, Any]] = None
                                     ) -> List[Tuple[List[Union[KnowledgeData, OperationalData]], str]]: # Corrected line
        """
        Identifies sets of KnowledgeData or OperationalData items that are candidates for collapse
        based on configured patterns (e.g., repetition, symbolic echoes, frequency, co-occurrence).

        Args:
            data_type (str): 'knowledge' or 'operational' to specify which data to scan.
            pattern_config (Optional[Dict[str, Any]]): Configuration for pattern detection.
                                                       Example for Frequency: {"type": "frequency", "min_threshold": 3, "group_by_field": "type"}

        Returns:
            List[Tuple[List[Union[KnowledgeData, OperationalData]], str]]: 
                A list of tuples, where each tuple contains:
                - A list of source data items (KnowledgeData or OperationalData instances).
                - A string describing the type of pattern identified (e.g., "frequency_knowledge_type_error_log").
        """
        logger.info(f"Identifying collapse candidates for data_type: {data_type} with config: {pattern_config}")
        candidates: List[Tuple[List[Union[KnowledgeData, OperationalData]], str]] = []
        
        active_pattern_config = pattern_config or {}
        pattern_detection_type = active_pattern_config.get("type", "frequency")

        if pattern_detection_type == "frequency":
            min_threshold = active_pattern_config.get("min_threshold", DEFAULT_FREQUENCY_THRESHOLD)
            group_by_field = active_pattern_config.get("group_by_field", "type") 

            if data_type == "knowledge":
                try:
                    all_knowledge_ids = self.catalog_service.list_knowledge_items()
                    all_knowledge_items: List[KnowledgeData] = []
                    for kd_id in all_knowledge_ids:
                        item = self.catalog_service.get_knowledge(kd_id)
                        if item: all_knowledge_items.append(item)
                    logger.info(f"Fetched {len(all_knowledge_items)} KnowledgeData items for frequency analysis.")

                    if not all_knowledge_items:
                        logger.info("No KnowledgeData items found to analyze for frequency.")
                        return []

                    grouped_items: Dict[str, List[KnowledgeData]] = {}
                    for item in all_knowledge_items:
                        group_key_value = getattr(item, group_by_field, None)
                        if group_key_value is not None:
                            if not isinstance(group_key_value, str):
                                group_key_value = str(group_key_value)
                            grouped_items.setdefault(group_key_value, []).append(item)
                    
                    for group_value, items_in_group in grouped_items.items():
                        if len(items_in_group) >= min_threshold:
                            pattern_name = f"frequency_knowledge_{group_by_field}_{group_value.replace(' ', '_').lower()}"
                            candidates.append((items_in_group, pattern_name))
                            logger.info(f"Identified candidate group: '{pattern_name}' with {len(items_in_group)} items.")

                except DataCatalogException as e:
                    logger.error(f"DataCatalogException while fetching KnowledgeData for frequency pattern: {e}")
                    return []
                except Exception as e:
                    logger.error(f"Unexpected error during frequency pattern detection for KnowledgeData: {e}", exc_info=True)
                    return [] 

            elif data_type == "operational":
                logger.warning("Frequency pattern detection for 'operational' data_type is not yet implemented.")
            else:
                logger.warning(f"Unsupported data_type '{data_type}' for frequency pattern detection.")
        
        else:
            logger.warning(f"Pattern detection type '{pattern_detection_type}' is not implemented.")

        if not candidates:
            logger.info("No collapse candidates identified.")
        return candidates

    def create_mythic_object_from_candidates(self, 
                                             source_items: List[Union[KnowledgeData, OperationalData]], 
                                             pattern_type: str, 
                                             mythic_object_type_override: Optional[str] = None
                                             ) -> Optional[MythicObject]: # Corrected here too potentially
        if not source_items:
            logger.warning("Cannot create MythicObject: source_items is empty.")
            return None

        source_ids = []
        all_tags = set()
        source_contents_list = []
        common_item_type_value = None 
        source_data_category = "unknown"

        for item in source_items:
            if isinstance(item, KnowledgeData):
                source_data_category = "KnowledgeData"
                source_ids.append(item.knowledge_id)
                if item.tags: all_tags.update(item.tags)
                source_contents_list.append(item.content) 
                if common_item_type_value is None: common_item_type_value = item.type
            elif isinstance(item, OperationalData):
                source_data_category = "OperationalData"
                source_ids.append(item.operation_id)
                if item.tags: all_tags.update(item.tags)
                op_content = {"task_type": item.task_type, "status": item.status, "inputs": item.inputs, "outputs": item.outputs}
                source_contents_list.append(op_content)
                if common_item_type_value is None: common_item_type_value = item.task_type
            else:
                logger.warning(f"Unsupported item type in source_items for MythicObject creation: {type(item)}")
                continue
        
        if not source_ids:
            logger.warning("No valid source IDs found for MythicObject creation after filtering items.")
            return None

        mo_type = mythic_object_type_override if mythic_object_type_override else pattern_type

        final_collapsed_content = {
            "original_pattern_type": pattern_type, 
            "source_data_category": source_data_category, 
            "collapsed_item_group_value": common_item_type_value, 
            "count": len(source_ids),
            "source_contents": source_contents_list, 
            "merged_tags": list(all_tags)
        }

        try:
            mythic_obj = MythicObject(
                source_ids=list(set(source_ids)), 
                type=mo_type,
                collapsed_content=final_collapsed_content,
                tags=list(all_tags)
            )
            logger.info(f"Prepared MythicObject (ID: {mythic_obj.id}) of type '{mo_type}' from {len(source_ids)} items.")
            return mythic_obj
        except Exception as e:
            logger.error(f"Error creating MythicObject instance: {e}", exc_info=True)
            return None

    def create_mythic_links(self, 
                            mythic_objects: List[MythicObject], 
                            link_logic_config: Optional[Dict[str, Any]] = None
                            ) -> List[MythicLink]: # Corrected here too potentially
        logger.info(f"create_mythic_links called for {len(mythic_objects)} objects. No inter-object links will be created in this version.")
        return []

    def perform_ritual_collapse(self, 
                                data_type: str = "knowledge", 
                                pattern_config: Optional[Dict[str, Any]] = None, 
                                link_logic_config: Optional[Dict[str, Any]] = None,
                                mythic_object_type_override: Optional[str] = None
                                ) -> Tuple[List[MythicObject], List[MythicLink]]: # Corrected here too potentially
        logger.info(f"Starting Ritual Collapse for data_type='{data_type}'.")
        
        all_persisted_mythic_objects: List[MythicObject] = []
        all_persisted_mythic_links: List[MythicLink] = []

        candidate_groups = self.identify_collapse_candidates(data_type, pattern_config)

        if not candidate_groups:
            logger.info("No candidate groups found. Ritual Collapse concludes.")
            return [], []

        logger.info(f"Identified {len(candidate_groups)} candidate group(s) for collapse.")

        for source_items, identified_pattern_type in candidate_groups:
            mythic_obj_instance = self.create_mythic_object_from_candidates(
                source_items,
                identified_pattern_type,
                mythic_object_type_override=mythic_object_type_override
            )
            if mythic_obj_instance:
                try:
                    success = self.catalog_service.register_mythic_object(mythic_obj_instance)
                    if success:
                        all_persisted_mythic_objects.append(mythic_obj_instance)
                        logger.info(f"Successfully registered MythicObject ID: {mythic_obj_instance.id}")
                    else:
                        logger.error(f"Failed to register MythicObject ID: {mythic_obj_instance.id} - catalog returned False.")
                except (StorageFailure, OperationFailure, DataCatalogException) as e_store:
                    logger.error(f"Error persisting MythicObject (ID: {mythic_obj_instance.id}): {e_store}")
                except Exception as e_unexpected:
                    logger.error(f"Unexpected error persisting MythicObject (ID: {mythic_obj_instance.id}): {e_unexpected}", exc_info=True)

        if not all_persisted_mythic_objects:
            logger.info("No MythicObjects were successfully created and persisted. Ritual Collapse concludes.")
            return [], []

        logger.info(f"Successfully created and persisted {len(all_persisted_mythic_objects)} MythicObject(s).")

        links_to_create = self.create_mythic_links(all_persisted_mythic_objects, link_logic_config)
        if links_to_create:
            logger.info(f"Attempting to persist {len(links_to_create)} MythicLink(s)...")
            for link_instance in links_to_create:
                try:
                    success = self.catalog_service.register_mythic_link(link_instance)
                    if success:
                        all_persisted_mythic_links.append(link_instance)
                        logger.info(f"Successfully registered MythicLink ID: {link_instance.id}")
                    else:
                        logger.error(f"Failed to register MythicLink ID: {link_instance.id} - catalog returned False.")
                except (StorageFailure, OperationFailure, DataCatalogException) as e_store_link:
                    logger.error(f"Error persisting MythicLink (ID: {link_instance.id}): {e_store_link}")
                except Exception as e_unexpected_link:
                    logger.error(f"Unexpected error persisting MythicLink (ID: {link_instance.id}): {e_unexpected_link}", exc_info=True)
        else:
            logger.info("No MythicLinks were generated to persist.")

        logger.info(f"Ritual Collapse completed. Persisted {len(all_persisted_mythic_objects)} MythicObjects and {len(all_persisted_mythic_links)} MythicLinks.")
        return all_persisted_mythic_objects, all_persisted_mythic_links

if __name__ == '__main__':
    from vanta_seed.services.data_catalog_service import DataCatalogService
    # KnowledgeData schema is already imported at the top of the file if needed directly
    # from vanta_seed.schemas.memory_agent_schemas import KnowledgeData 

    catalog = None
    created_mythic_object_ids_for_cleanup = []
    knowledge_data_ids_for_cleanup = []

    try:
        catalog = DataCatalogService() # Initialize DataCatalogService
        if not catalog.client: # Basic check if client initialization within catalog service was successful
            print("Failed to initialize DataCatalogService client. Aborting test.")
            exit(1)

        print("--- Populating KnowledgeData for Ritual Collapse Test ---")
        sample_data_payloads = [
            {"knowledge_id": "freq_kd_1", "source_session_ids": ["session_freq_test"], "type": "error_log", "content": {"error_code": 500, "message": "Service A unresponsive"}, "tags": ["system", "error", "service_a"]},
            {"knowledge_id": "freq_kd_2", "source_session_ids": ["session_freq_test"], "type": "error_log", "content": {"error_code": 503, "message": "Service B timeout"}, "tags": ["system", "error", "service_b"]},
            {"knowledge_id": "freq_kd_3", "source_session_ids": ["session_freq_test"], "type": "error_log", "content": {"error_code": 500, "message": "Service A DB connection failed"}, "tags": ["system", "error", "service_a", "database"]},
            {"knowledge_id": "freq_kd_4", "source_session_ids": ["session_freq_test_other"], "type": "audit_log", "content": {"action": "user_login", "user_id": "user123"}, "tags": ["system", "audit", "security"]},
            {"knowledge_id": "freq_kd_5", "source_session_ids": ["session_freq_test_other"], "type": "audit_log", "content": {"action": "user_logout", "user_id": "user123"}, "tags": ["system", "audit"]}
        ]

        for payload in sample_data_payloads:
            item = KnowledgeData(**payload) # Create model instance
            catalog.register_knowledge(item)
            knowledge_data_ids_for_cleanup.append(item.knowledge_id)
            print(f"Registered KnowledgeData: {item.knowledge_id} of type '{item.type}'")
        
        print(f"\n--- Running RitualCollapseService --- ")
        collapse_service = RitualCollapseService(catalog)
        
        freq_pattern_cfg = {"type": "frequency", "min_threshold": DEFAULT_FREQUENCY_THRESHOLD, "group_by_field": "type"}
        
        mythic_objects, mythic_links = collapse_service.perform_ritual_collapse(
            data_type="knowledge",
            pattern_config=freq_pattern_cfg
        )

        print("\n--- Ritual Collapse Results ---")
        if mythic_objects:
            print(f"Created and persisted {len(mythic_objects)} MythicObjects:")
            for obj in mythic_objects:
                created_mythic_object_ids_for_cleanup.append(obj.id)
                print(obj.model_dump_json(indent=2))
                if obj.collapsed_content.get("collapsed_item_group_value") == "error_log":
                    assert obj.collapsed_content.get("count") == 3, "Incorrect count for error_log collapse"
                    assert len(obj.source_ids) == 3, "Incorrect number of source_ids for error_log collapse"
                    assert "error" in obj.tags, "Missing merged tag 'error'"
        else:
            print("No MythicObjects created or persisted.")

        if mythic_links:
            print(f"\nCreated and persisted {len(mythic_links)} MythicLinks:")
            for link in mythic_links:
                print(link.model_dump_json(indent=2))
        else:
            print("No MythicLinks created or persisted (as expected for this version).")

        stored_mythic_object_details = []
        if created_mythic_object_ids_for_cleanup:
            print("\n--- Verifying Stored Mythic Objects via get_mythic_object ---")
            for mo_id in created_mythic_object_ids_for_cleanup:
                retrieved_mo = catalog.get_mythic_object(mo_id)
                if retrieved_mo:
                    stored_mythic_object_details.append(retrieved_mo)
                    print(f"Retrieved MythicObject ID {mo_id} successfully.")
                else:
                    print(f"FAILED to retrieve MythicObject ID {mo_id}.")
            assert len(stored_mythic_object_details) == len(created_mythic_object_ids_for_cleanup), "Mismatch in number of created vs retrieved mythic objects."

        print("\nTest execution completed.")

    except Exception as e:
        print(f"An error occurred during the test: {e}", exc_info=True)
    
    finally:
        if catalog:
            print("\n--- Cleaning up Test Data ---")
            for mo_id in created_mythic_object_ids_for_cleanup:
                if catalog.delete_mythic_object(mo_id):
                    print(f"Deleted MythicObject: {mo_id}")
                else:
                    print(f"Failed to delete MythicObject: {mo_id}")
            
            for kd_id in knowledge_data_ids_for_cleanup:
                if catalog.delete_knowledge(kd_id):
                    print(f"Deleted KnowledgeData: {kd_id}")
                else:
                    print(f"Failed to delete KnowledgeData: {kd_id}")

            print("Test data cleanup attempt complete.")
            catalog.close_qdrant_client()
            print("Qdrant client closed.") 