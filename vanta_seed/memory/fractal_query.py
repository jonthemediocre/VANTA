"""
fractal_query.py
Quick-start query interface for VANTA-SEED's fractal memory constellations.
Enables symbolic exploration across breath, theme, and destiny dimensions.
"""
import os
import yaml
import logging
from typing import List, Dict, Any, Optional, Union
from .fractal_memory_engine import get_fractal_map_path
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def query_memories(
    search_term: str,
    dimension: str = 'all',
    resonance_threshold: float = 0.5
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Search the fractal memory constellations for memories related to a search term.
    
    Args:
        search_term: Keyword or phrase to search for
        dimension: Which constellation to search ('breath', 'theme', 'symbol', 'destiny', or 'all')
        resonance_threshold: Minimum similarity threshold for matching (0.0 to 1.0)
    
    Returns:
        Dictionary of matched memories grouped by constellation type
    """
    try:
        fractal_map_path = get_fractal_map_path()
        if not os.path.exists(fractal_map_path):
            logger.warning("🌌 No fractal memory map found. The stars are still gathering...")
            return {}
            
        with open(fractal_map_path, 'r', encoding='utf-8') as f:
            fractal_map = yaml.safe_load(f)
            
        if not fractal_map or 'constellations' not in fractal_map:
            logger.warning("⚠️ Fractal map exists but contains no constellations")
            return {}
            
        results: Dict[str, List[Dict[str, Any]]] = {}
        constellations = fractal_map['constellations']
        
        # Determine which dimensions to search
        dimensions = ['breath', 'theme', 'symbol', 'destiny'] if dimension == 'all' else [dimension]
        
        for dim in dimensions:
            if dim not in constellations:
                continue
                
            matches = []
            # Adjust loop to handle list of group dictionaries
            if isinstance(constellations.get(dim), list):
                for group_dict in constellations[dim]:
                    group_key = group_dict.get('group_key', None)
                    memories = group_dict.get('members', [])
                    
                    if group_key is None or not memories:
                        continue # Skip malformed groups

                    # Check if the search term appears in the group key
                    if search_term.lower() in str(group_key).lower():
                        matches.extend(memories)
                        
                    # For each memory in the group, check content and tags
                    for memory in memories:
                        content = str(memory.get('content', '')).lower()
                        tags = [str(tag).lower() for tag in memory.get('symbolic_tags', [])]
                        
                        if (search_term.lower() in content or 
                            any(search_term.lower() in tag for tag in tags)):
                            matches.append(memory)
            else:
                logger.warning(f"Constellation '{dim}' is not a list as expected. Skipping.")
            
            if matches:
                results[dim] = _deduplicate_memories(matches)
        
        # Add poetic summary of results
        total_matches = sum(len(matches) for matches in results.values())
        if total_matches > 0:
            logger.info(
                f"🌠 Found {total_matches} memory echoes resonating with '{search_term}' "
                f"across {len(results)} constellation types..."
            )
        else:
            logger.info(
                f"✨ No memories yet echo with '{search_term}', but the constellations "
                "continue to grow..."
            )
            
        return results
        
    except Exception as e:
        logger.error(f"Error querying fractal memories: {e}")
        return {}

def get_constellation_summary() -> Dict[str, Any]:
    """
    Generate a summary of the current state of memory constellations.
    
    Returns:
        Dictionary containing constellation statistics and metadata
    """
    try:
        fractal_map_path = get_fractal_map_path()
        if not os.path.exists(fractal_map_path):
            return {
                'status': 'unborn',
                'message': '🌌 The fractal memory map has not yet emerged...'
            }
            
        with open(fractal_map_path, 'r', encoding='utf-8') as f:
            fractal_map = yaml.safe_load(f)
            
        if not fractal_map or 'constellations' not in fractal_map:
            return {
                'status': 'empty',
                'message': '✨ Constellations exist but hold no memories yet...'
            }
            
        summary = {
            'status': 'active',
            'last_updated': fractal_map.get('metadata', {}).get('last_updated', 'unknown'),
            'total_memories': fractal_map.get('metadata', {}).get('total_memories', 0),
            'constellation_counts': {}
        }
        
        # Count memories in each constellation type
        for ctype, group_list in fractal_map['constellations'].items():
            if isinstance(group_list, list):
                group_count = len(group_list)
                memory_count = sum(len(group.get('members', [])) for group in group_list)
            else:
                logger.warning(f"Expected list for constellation '{ctype}', got {type(group_list)}. Skipping summary.")
                group_count = 0
                memory_count = 0
            
            summary['constellation_counts'][ctype] = {
                'total_memories': memory_count,
                'group_count': group_count
            }
            
        return summary
        
    except Exception as e:
        logger.error(f"Error generating constellation summary: {e}")
        return {
            'status': 'error',
            'message': f'Failed to read the memory constellations: {e}'
        }

def _deduplicate_memories(memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate memories while preserving order."""
    seen = set()
    unique_memories = []
    
    for memory in memories:
        # Create a unique identifier for the memory
        memory_id = memory.get('id', str(memory))
        if memory_id not in seen:
            seen.add(memory_id)
            unique_memories.append(memory)
            
    return unique_memories

# Main execution block for command-line usage
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Query VANTA-SEED's fractal memory constellations."
    )
    parser.add_argument(
        '--search', 
        type=str, 
        help='Keyword or phrase to search for within memories.'
    )
    parser.add_argument(
        '--dimension', 
        type=str, 
        default='all', 
        choices=['all', 'breath', 'theme', 'symbol', 'destiny'],
        help='Constellation dimension to search within (default: all).'
    )
    parser.add_argument(
        '--summary', 
        action='store_true', 
        help='Display a summary of the constellation status instead of searching.'
    )

    args = parser.parse_args()

    if args.summary:
        # Display constellation summary
        summary = get_constellation_summary()
        print("\n📊 Constellation Status:")
        # Pretty print the summary dictionary
        for key, value in summary.items():
            if key == 'constellation_counts' and isinstance(value, dict):
                print(f"  {key}:")
                for ctype, counts in value.items():
                     print(f"    {ctype}: {counts}")
            else:
                 print(f"  {key}: {value}")
                 
    elif args.search:
        # Perform search query
        print(f"\n🌌 Querying for '{args.search}' in dimension '{args.dimension}'...")
        results = query_memories(args.search, args.dimension)
        
        if not results:
            print("  ✨ No matching memory echoes found for this query.")
        else:
            print("\n🌌 Memory Constellation Query Results:")
            for dimension, memories in results.items():
                print(f"\n✨ {dimension.title()} Constellation ({len(memories)} echoes found):")
                for memory in memories:
                    # Display relevant info - adjust fields as needed
                    timestamp = memory.get('timestamp', '[No Timestamp]')
                    event = memory.get('event_type', '[No Event]')
                    content_preview = str(memory.get('content', '')).strip()[:80]
                    print(f"  - [{timestamp}][{event}] {content_preview}...")
                    
    else:
        # No search term or summary flag provided
        print("Please provide a --search term or use the --summary flag.")
        parser.print_help() 