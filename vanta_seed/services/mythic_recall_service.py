import logging
from typing import List, Optional, Dict, Any, Set, Tuple

from vanta_seed.services.data_catalog_service import DataCatalogService
from vanta_seed.schemas.mythic_schemas import MythicObject, MythicLink
# Potentially KnowledgeData, OperationalData if we fetch full source items
from vanta_seed.schemas.memory_agent_schemas import KnowledgeData, OperationalData 
from vanta_seed.exceptions import NotFound, DataCatalogException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class NarrativePath(BaseModel):
    """Pydantic model to represent a structured narrative path or graph."""
    entry_object_id: str
    objects: Dict[str, MythicObject] = Field(default_factory=dict) # object_id -> MythicObject
    links: List[MythicLink] = Field(default_factory=list)
    # Optional: Include full source data for objects in the path
    # source_data_cache: Dict[str, Union[KnowledgeData, OperationalData]] = Field(default_factory=dict)

    class Config:
        extra = 'allow'

class MythicRecallService:
    """
    Service responsible for retrieving MythicObjects and traversing MythicLinks 
    to construct narrative paths or story graphs.
    """

    def __init__(self, data_catalog_service: DataCatalogService):
        if not data_catalog_service:
            logger.error("MythicRecallService initialized with a null DataCatalogService.")
            raise ValueError("DataCatalogService cannot be None for MythicRecallService.")
        self.catalog_service = data_catalog_service
        logger.info("MythicRecallService initialized.")

    def get_mythic_object_with_direct_links(self, mythic_object_id: str) -> Optional[NarrativePath]:
        """
        Retrieves a specific MythicObject and all MythicLinks directly connected to it,
        along with the MythicObjects at the other end of those links.

        Args:
            mythic_object_id (str): The ID of the MythicObject to start from.

        Returns:
            Optional[NarrativePath]: A NarrativePath object containing the central object,
                                     its direct links, and connected objects, or None if not found.
        """
        logger.info(f"Fetching MythicObject '{mythic_object_id}' with direct links.")
        try:
            central_object = self.catalog_service.get_mythic_object(mythic_object_id)
            if not central_object:
                logger.warning(f"MythicObject '{mythic_object_id}' not found.")
                return None

            narrative = NarrativePath(entry_object_id=central_object.id)
            narrative.objects[central_object.id] = central_object
            
            # Find links where this object is the source or target
            # This requires a way to query links by source_object_id or target_object_id.
            # DataCatalogService will need to be extended for this query pattern if not already supported.
            # For now, assume we fetch all links and filter (inefficient for large datasets).
            all_links = self.catalog_service.list_mythic_links() # Returns list of IDs
            relevant_links: List[MythicLink] = []
            neighbor_object_ids: Set[str] = set()

            logger.warning("Fetching all links to find direct connections. Consider optimizing DataCatalogService for link queries.")
            for link_id in all_links:
                link = self.catalog_service.get_mythic_link(link_id)
                if link:
                    if link.source_object_id == mythic_object_id:
                        relevant_links.append(link)
                        neighbor_object_ids.add(link.target_object_id)
                    elif link.target_object_id == mythic_object_id:
                        relevant_links.append(link)
                        neighbor_object_ids.add(link.source_object_id)
            
            narrative.links.extend(relevant_links)

            for neighbor_id in neighbor_object_ids:
                if neighbor_id not in narrative.objects: # Avoid re-fetching central object
                    neighbor_object = self.catalog_service.get_mythic_object(neighbor_id)
                    if neighbor_object:
                        narrative.objects[neighbor_id] = neighbor_object
                    else:
                        logger.warning(f"Neighbor MythicObject '{neighbor_id}' linked from/to '{mythic_object_id}' not found.")
            
            logger.info(f"Found {len(narrative.links)} direct links and {len(narrative.objects)-1} neighbors for MythicObject '{mythic_object_id}'.")
            return narrative

        except DataCatalogException as e:
            logger.error(f"DataCatalogException while getting mythic object '{mythic_object_id}' with links: {e}")
            return None # Or re-raise as a MythicRecallService specific exception
        except Exception as e:
            logger.error(f"Unexpected error getting mythic object '{mythic_object_id}' with links: {e}", exc_info=True)
            return None

    def trace_narrative_path(self, 
                             start_object_id: str, 
                             max_depth: int = 3, 
                             link_types_to_follow: Optional[List[str]] = None,
                             include_source_data: bool = False) -> Optional[NarrativePath]:
        """
        Traces a narrative path starting from a given MythicObject, following links up to a max_depth.

        Args:
            start_object_id (str): The ID of the MythicObject to start the trace from.
            max_depth (int): Maximum number of link traversals from the start object.
            link_types_to_follow (Optional[List[str]]): Specific link_type values to follow. If None, follows all.
            include_source_data (bool): If True, attempts to fetch and include the original source data
                                        (KnowledgeData/OperationalData) for each MythicObject in the path.

        Returns:
            Optional[NarrativePath]: A NarrativePath object representing the traced story, or None if start object not found.
        """
        logger.info(f"Tracing narrative path from '{start_object_id}' (max_depth: {max_depth}, link_types: {link_types_to_follow}, sources: {include_source_data}).")
        
        try:
            start_object = self.catalog_service.get_mythic_object(start_object_id)
            if not start_object:
                logger.warning(f"Start MythicObject '{start_object_id}' not found for narrative trace.")
                return None

            narrative = NarrativePath(entry_object_id=start_object_id)
            narrative.objects[start_object_id] = start_object

            # Queue for BFS-like traversal: (object_id, current_depth)
            queue: List[Tuple[str, int]] = [(start_object_id, 0)]
            visited_object_ids: Set[str] = {start_object_id}
            visited_link_ids: Set[str] = set()

            # Inefficiently fetching all links for now. DataCatalogService needs better query capabilities.
            all_link_ids = self.catalog_service.list_mythic_links()
            all_links_map: Dict[str, List[MythicLink]] = {} # source_id -> list of links from it
            if all_link_ids:
                logger.warning("Fetching all links to trace narrative. Optimize DataCatalogService for link queries by source_id.")
                for link_id in all_link_ids:
                    link = self.catalog_service.get_mythic_link(link_id)
                    if link:
                        all_links_map.setdefault(link.source_object_id, []).append(link)

            while queue:
                current_obj_id, current_depth = queue.pop(0)

                if current_depth >= max_depth:
                    continue

                # Find outgoing links from current_obj_id
                # This part needs efficient querying of links by source_object_id from DataCatalogService.
                # Using pre-fetched all_links_map for now.
                outgoing_links = all_links_map.get(current_obj_id, [])
                
                for link in outgoing_links:
                    if link.id in visited_link_ids:
                        continue # Avoid processing the same link twice if graph is cyclic
                    
                    if link_types_to_follow and link.link_type not in link_types_to_follow:
                        continue # Skip link if its type is not in the desired list

                    narrative.links.append(link)
                    visited_link_ids.add(link.id)
                    
                    target_obj_id = link.target_object_id
                    if target_obj_id not in narrative.objects:
                        target_object = self.catalog_service.get_mythic_object(target_obj_id)
                        if target_object:
                            narrative.objects[target_obj_id] = target_object
                        else:
                            logger.warning(f"Target MythicObject '{target_obj_id}' in link '{link.id}' not found.")
                            continue # Don't add to queue if target doesn't exist
                    
                    if target_obj_id not in visited_object_ids:
                        visited_object_ids.add(target_obj_id)
                        queue.append((target_obj_id, current_depth + 1))
            
            # Optional: Fetch source data if requested
            # if include_source_data:
            #     logger.info("Fetching source data for MythicObjects in the narrative path...")
            #     for obj_id, mythic_obj in narrative.objects.items():
            #         for source_id in mythic_obj.source_ids:
            #             # This needs to know if source_id refers to KnowledgeData or OperationalData
            #             # Requires a more robust way to determine source type or try fetching from both.
            #             # Placeholder logic:
            #             logger.warning("Source data fetching is a placeholder and needs robust type determination.")
            #             # knowledge_item = self.catalog_service.get_knowledge(source_id)
            #             # if knowledge_item: narrative.source_data_cache[source_id] = knowledge_item
            #             # else:
            #             #     op_item = self.catalog_service.get_operational(source_id)
            #             #     if op_item: narrative.source_data_cache[source_id] = op_item
            #             pass # End placeholder

            logger.info(f"Narrative trace for '{start_object_id}' complete. Path contains {len(narrative.objects)} objects and {len(narrative.links)} links.")
            return narrative

        except DataCatalogException as e:
            logger.error(f"DataCatalogException during narrative trace for '{start_object_id}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during narrative trace for '{start_object_id}': {e}", exc_info=True)
            return None

# Example Usage (Conceptual - requires a running DataCatalogService populated with MythicObjects and MythicLinks)
# if __name__ == "__main__":
#     from vanta_seed.services.data_catalog_service import DataCatalogService
#     # Assume catalog_service is initialized
#     # catalog = DataCatalogService()
#     # if catalog.client:
#     #     recall_service = MythicRecallService(catalog)

#     #     # Assume some MythicObjects (mo1_id, mo2_id, mo3_id) and Links exist
#     #     # mo1_id = "... some existing mythic object id ..."

#     #     # Test 1: Get an object with its direct links
#     #     print(f"\n--- Test: Get MythicObject with Direct Links for {mo1_id} ---")
#     #     direct_narrative = recall_service.get_mythic_object_with_direct_links(mo1_id)
#     #     if direct_narrative:
#     #         print(f"Entry Object ID: {direct_narrative.entry_object_id}")
#     #         print(f"Found {len(direct_narrative.objects)} objects:")
#     #         for obj_id, obj_data in direct_narrative.objects.items():
#     #             print(f"  ID: {obj_id}, Type: {obj_data.type}")
#     #         print(f"Found {len(direct_narrative.links)} links:")
#     #         for link_data in direct_narrative.links:
#     #             print(f"  Link ID: {link_data.id}, Type: {link_data.link_type}, From: {link_data.source_object_id} To: {link_data.target_object_id}")
#     #     else:
#     #         print(f"Could not retrieve direct narrative for {mo1_id}.")

#     #     # Test 2: Trace a narrative path
#     #     print(f"\n--- Test: Trace Narrative Path from {mo1_id} ---")
#     #     traced_narrative = recall_service.trace_narrative_path(start_object_id=mo1_id, max_depth=2)
#     #     if traced_narrative:
#     #         print(f"Narrative trace starting from: {traced_narrative.entry_object_id}")
#     #         print(f"Path contains {len(traced_narrative.objects)} objects:")
#     #         for obj_id, obj_data in traced_narrative.objects.items():
#     #             print(f"  ID: {obj_id}, Type: {obj_data.type}, Sources: {obj_data.source_ids}")
#     #         print(f"Path contains {len(traced_narrative.links)} links:")
#     #         for link_data in traced_narrative.links:
#     #             print(f"  Link ID: {link_data.id}, Type: {link_data.link_type}, From: {link_data.source_object_id} To: {link_data.target_object_id}")
#     #     else:
#     #         print(f"Could not trace narrative for {mo1_id}.")

#     #     catalog.close_qdrant_client()
#     # else:
#     #     print("Failed to initialize DataCatalogService for MythicRecallService test.")

# Need to import BaseModel for NarrativePath
# from pydantic import BaseModel, Field 