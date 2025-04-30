"""
fractal_memory_engine.py
Fractal Memory Engine for VANTA-SEED: Symbolic, constellation-based memory linking and retrieval.
"""
import os
import yaml
import json
import glob
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_memory_storage_path() -> str:
    """Get the path to the memory storage directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, 'memory_storage')

def get_fractal_map_path() -> str:
    """Get the path for saving the fractal memory map."""
    return os.path.join(get_memory_storage_path(), 'fractal_memory_map.yaml')

def load_all_memories() -> List[Dict[str, Any]]:
    """
    Load all memory entries from JSONL files in memory_storage.
    Returns a list of memory objects, skipping invalid entries.
    """
    storage_path = get_memory_storage_path()
    all_memories = []
    
    # Create storage directory if it doesn't exist
    os.makedirs(storage_path, exist_ok=True)
    
    # Find all JSONL files in memory_storage
    jsonl_pattern = os.path.join(storage_path, '*.jsonl')
    memory_files = glob.glob(jsonl_pattern)
    
    if not memory_files:
        logger.warning(f"No memory files found in {storage_path}")
        return []
    
    for file_path in memory_files:
        logger.info(f"Processing memory file: {os.path.basename(file_path)}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        # Skip empty lines
                        if not line.strip():
                            continue
                        
                        # Parse JSONL entry
                        memory = json.loads(line)
                        
                        # --- Modified Validation & Content Extraction ---
                        # 1. Check for event_type (still required)
                        if 'event_type' not in memory:
                            logger.warning(
                                f"Skipping memory in {os.path.basename(file_path)} line {line_num}: "
                                "Missing required field 'event_type'"
                            )
                            continue
                            
                        # 2. Handle content (use 'details' as fallback)
                        if 'content' not in memory:
                            if 'details' in memory:
                                details_data = memory['details']
                                # Convert dict details to string, use string details directly
                                if isinstance(details_data, dict):
                                    memory['content'] = json.dumps(details_data, sort_keys=True)
                                else:
                                    memory['content'] = str(details_data)
                                logger.debug(
                                    f"Used 'details' as fallback for 'content' in "
                                    f"{os.path.basename(file_path)} line {line_num}"
                                )
                            else:
                                # If neither content nor details exist, it fails validation
                                logger.warning(
                                    f"Skipping memory in {os.path.basename(file_path)} line {line_num}: "
                                    "Missing required field 'content' (and no 'details' fallback)"
                                )
                                continue
                        # --- End Modification ---
                        
                        # Add the validated (and potentially modified) memory to collection
                        all_memories.append(memory)
                        
                    except json.JSONDecodeError as e:
                        logger.warning(
                            f"Invalid JSON in {os.path.basename(file_path)} line {line_num}: {e}"
                        )
                        continue
                    except Exception as e:
                        logger.warning(
                            f"Error processing memory in {os.path.basename(file_path)} "
                            f"line {line_num}: {e}"
                        )
                        continue
                        
        except Exception as e:
            logger.error(f"Error reading memory file {file_path}: {e}")
            continue
    
    logger.info(f"Loaded {len(all_memories)} valid memories from storage")
    return all_memories

def create_fractal_links(memory_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Parses JSON-serialized `content` from each record (or dict directly),
    then groups by breath_number, theme, symbolic_tags, and destiny_path.
    Returns a structured map with constellations as lists of groups.
    """
    constellations = {'breath': {}, 'theme': {}, 'symbol': {}, 'destiny': {}}
    processed_record_ids = set()

    for record in memory_records:
        # Generate a unique ID for deduplication within this processing run
        record_id = record.get('timestamp', str(record))
        if record_id in processed_record_ids:
            continue
        processed_record_ids.add(record_id)

        content = record.get('content')
        details = None

        # 1) Parse serialized JSON or accept dict
        if isinstance(content, str):
            try:
                details = json.loads(content)
            except (TypeError, json.JSONDecodeError):
                logger.debug(f"Could not parse content as JSON for record: {record_id}")
                details = {'content_raw': content} # Store raw content if parsing fails
        elif isinstance(content, dict):
             # If content itself is already a dict (e.g., from fallback logic)
             details = content
        else:
             logger.debug(f"Content field is neither string nor dict for record: {record_id}")
             continue # Skip if content is not parseable/usable

        if not isinstance(details, dict):
            logger.debug(f"Parsed/retrieved details is not a dict for record: {record_id}")
            continue

        # 2) Extract keys with sensible defaults
        # Use get with defaults to avoid KeyError
        breath_num    = str(details.get('breath_number', record.get('breath_number', 'unknown'))) # Fallback to top-level if needed
        theme         = str(details.get('theme', record.get('theme', 'unthemed')))
        # Ensure tags are a list of strings
        symbolic_tags_raw = details.get('symbolic_tags', record.get('symbolic_tags', []))
        symbolic_tags = [str(tag) for tag in symbolic_tags_raw if isinstance(tag, (str, int, float))] if isinstance(symbolic_tags_raw, list) else []
        destiny_path  = str(details.get('destiny_path', record.get('destiny', 'undecided')))

        # Add extracted fields back to the main record for consistency in the map?
        # Optional: record['parsed_breath'] = breath_num etc.

        # 3) Populate grouping buckets
        constellations['breath'].setdefault(breath_num, []).append(record)
        constellations['theme'].setdefault(theme, []).append(record)
        constellations['destiny'].setdefault(destiny_path, []).append(record)
        for symbol in symbolic_tags:
            constellations['symbol'].setdefault(symbol, []).append(record)

    # 4) Convert mapping dicts into lists of {group_key, members}
    final_constellations = {}
    for key, groups in constellations.items():
        final_constellations[key] = [
            {'group_key': str(k), 'members': v}
            for k, v in groups.items()
        ]

    # Construct final map structure
    fractal_map = {
        'metadata': {
            'total_memories_processed': len(memory_records),
            'valid_memories_linked': len(processed_record_ids),
            'last_updated': None, # Will be set by save_fractal_map
            'constellation_types': list(final_constellations.keys())
            # schema_version will be added by save_fractal_map
        },
        'constellations': final_constellations,
        'links': [] # Keep placeholder for future cross-links
    }

    return fractal_map

def save_fractal_map(fractal_map: Dict[str, Any], path: Optional[str] = None) -> None:
    """Save the fractal memory map to YAML file."""
    if path is None:
        path = get_fractal_map_path()
    
    # --- Add/Update Metadata ---
    if 'metadata' not in fractal_map:
        fractal_map['metadata'] = {}
    
    # Calculate unique memories across all constellations from the input map
    unique_ids = set()
    if 'constellations' in fractal_map:
        for ctype, groups in fractal_map['constellations'].items():
            if isinstance(groups, list): # Check if it's the expected list of group dicts
                 for group in groups:
                     if isinstance(group, dict) and 'members' in group and isinstance(group['members'], list):
                         for record in group['members']:
                             if isinstance(record, dict): # Ensure record is a dict
                                 # Construct a stable identifier for each record
                                 ts = record.get('timestamp', '')
                                 et = record.get('event_type', '')
                                 # Add other potentially unique fields if needed, e.g., content hash
                                 identifier = f"{ts}::{et}" 
                                 unique_ids.add(identifier)
                     else:
                          logger.warning(f"Group {group.get('group_key', 'N/A')} in constellation '{ctype}' is not a valid dictionary or missing 'members'.")
            else:
                 logger.warning(f"Constellation '{ctype}' data is not a list as expected. Skipping for total_memories calculation.")

    fractal_map['metadata']['last_updated'] = datetime.now().isoformat() # Use .now() for local time or stick with utcnow() if preferred
    fractal_map['metadata']['total_memories'] = len(unique_ids) # Add the calculated count
    fractal_map['metadata']['schema_version'] = "1.1" # Reflects loader fix & metadata update
    # --- End Metadata Update ---
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    try:
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(fractal_map, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Fractal memory map saved to {path} (Total Unique Memories: {len(unique_ids)})") # Log the count
    except Exception as e:
        logger.error(f"Error saving fractal map to {path}: {e}")
        raise

def query_fractal_connections(query: Dict[str, Any], path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve memories from the fractal map based on symbolic nearness.
    Query can include: breath, theme, symbol, destiny, etc.
    """
    if path is None:
        path = get_fractal_map_path()
    
    if not os.path.exists(path):
        logger.warning(f"Fractal map not found at {path}")
        return []
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            fractal_map = yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Error reading fractal map from {path}: {e}")
        return []
    
    results = []
    
    # Search through each constellation type
    if 'constellations' in fractal_map:
        for constellation_type, groups in fractal_map['constellations'].items():
            if constellation_type in query:
                # Direct match in constellation
                if query[constellation_type] in groups:
                    results.extend(groups[query[constellation_type]])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_results = []
    for mem in results:
        mem_id = mem.get('id', json.dumps(mem, sort_keys=True))
        if mem_id not in seen:
            seen.add(mem_id)
            unique_results.append(mem)
    
    return unique_results 