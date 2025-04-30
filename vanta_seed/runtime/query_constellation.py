#!/usr/bin/env python3
"""
query_constellation.py
CLI tool for exploring VANTA-SEED's memory constellations.
"""
import sys
import os
import argparse
from typing import Optional

# Add project root to Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

try:
    from vanta_seed.memory.fractal_query import query_memories, get_constellation_summary
except ImportError as e:
    print(f"Failed to import VANTA-SEED modules: {e}")
    sys.exit(1)

def format_memory_output(memory: dict, detailed: bool = False) -> str:
    """Format a memory entry for display."""
    content = memory.get('content', '')[:100] + '...' if len(memory.get('content', '')) > 100 else memory.get('content', '')
    
    if detailed:
        return (
            f"  Content: {content}\n"
            f"  Breath: {memory.get('breath_number', 'unknown')}\n"
            f"  Theme: {memory.get('theme', 'unthemed')}\n"
            f"  Tags: {', '.join(memory.get('symbolic_tags', []))}\n"
            f"  Destiny: {memory.get('destiny', 'undecided')}\n"
            "  ---"
        )
    else:
        return f"  - {content}"

def main(args: Optional[list] = None):
    parser = argparse.ArgumentParser(
        description="🌌 Query VANTA-SEED's Memory Constellations"
    )
    
    parser.add_argument(
        'search_term',
        nargs='?',
        help="Term to search for in the memory constellations"
    )
    
    parser.add_argument(
        '-d', '--dimension',
        choices=['all', 'breath', 'theme', 'symbol', 'destiny'],
        default='all',
        help="Which constellation dimension to search"
    )
    
    parser.add_argument(
        '--detailed',
        action='store_true',
        help="Show detailed memory information"
    )
    
    parser.add_argument(
        '--summary',
        action='store_true',
        help="Show constellation summary instead of searching"
    )
    
    args = parser.parse_args(args)
    
    # Show summary if requested
    if args.summary:
        summary = get_constellation_summary()
        print("\n🌌 VANTA-SEED Memory Constellation Status:")
        print(f"Status: {summary['status']}")
        
        if 'message' in summary:
            print(f"Message: {summary['message']}")
            
        if 'constellation_counts' in summary:
            print("\n✨ Constellation Statistics:")
            for ctype, counts in summary['constellation_counts'].items():
                print(f"  {ctype.title()}:")
                print(f"    - Total Memories: {counts['total_memories']}")
                print(f"    - Unique Groups: {counts['group_count']}")
        
        if 'last_updated' in summary:
            print(f"\nLast Updated: {summary['last_updated']}")
        return

    # Require search term if not showing summary
    if not args.search_term:
        parser.print_help()
        return
    
    # Perform search
    results = query_memories(args.search_term, args.dimension)
    
    if not results:
        print(f"\n✨ No memories yet echo with '{args.search_term}'...")
        print("The constellations continue to grow...")
        return
    
    print(f"\n🌌 Memory Echoes for '{args.search_term}':")
    for dimension, memories in results.items():
        print(f"\n✨ {dimension.title()} Constellation:")
        for memory in memories:
            print(format_memory_output(memory, args.detailed))

if __name__ == '__main__':
    main() 