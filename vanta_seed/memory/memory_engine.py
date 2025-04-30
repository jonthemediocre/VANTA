# memory_engine.py
# Simple JSON Lines based memory storage

import json
import os
import logging
from datetime import datetime
import sqlite3
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any

# --- Configuration & Setup ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # vanta_seed directory
MEMORY_DIR = os.path.join(BASE_DIR, "memory_storage") # Store JSONL files here

logging.basicConfig(level=logging.INFO, format='%(asctime)s - MEM_ENGINE - %(levelname)s - %(message)s')

# Ensure memory storage directory exists
try:
    os.makedirs(MEMORY_DIR, exist_ok=True)
    logging.info(f"Memory storage directory ensured at: {MEMORY_DIR}")
except OSError as e:
    logging.error(f"Could not create memory storage directory {MEMORY_DIR}: {e}")
    # Attempting to continue, but saving might fail.

# --- FTS5 Integration ---

DB_PATH = Path(__file__).parents[1] / 'memory_storage' / 'memory_index.db'
JSONL_DIR = Path(__file__).parents[1] / 'memory_storage'

def query_memory_fts(search_term: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Perform FTS search on memory_index.db and return full original memory records.
    """
    if not DB_PATH.exists():
        logging.warning(f"FTS index database not found at {DB_PATH}. Cannot perform FTS query.")
        return []
        
    matched_docids = []
    conn = None
    try:
        # Use URI=True for potential future read-only connections if needed
        conn = sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True) 
        conn.row_factory = sqlite3.Row 

        sql = '''
        SELECT docid -- Only need docid to retrieve full record later
        FROM memory_fts
        WHERE content MATCH ? 
        ORDER BY rank -- Default FTS5 ranking
        LIMIT ?;
        '''
        
        cursor = conn.execute(sql, (search_term, limit))
        # Fetch all matching docids
        matched_docids = [row['docid'] for row in cursor.fetchall()]

    except sqlite3.Error as e:
        # Log specific SQLite errors
        logging.error(f"FTS query failed for term '{search_term}': {e}")
        return [] 
    except Exception as e:
        # Catch other potential errors
        logging.error(f"Unexpected error during FTS query: {e}")
        return []
    finally:
        if conn:
            conn.close()

    if not matched_docids:
        logging.info(f"FTS query for '{search_term}' returned no matches.")
        return [] # No matches found

    # Retrieve full records from JSONL based on docids
    logging.info(f"FTS query found {len(matched_docids)} potential matches. Retrieving full records...")
    full_results = get_memories_by_docids(matched_docids)
    return full_results

def get_memories_by_docids(docids: List[str]) -> List[Dict[str, Any]]:
    """
    Retrieve full memory records from JSONL files using docid (filename:linenum).
    Reads all lines of required files then accesses specific lines.
    """
    if not docids:
        return []

    # Group line numbers by filename
    grouped_by_file = defaultdict(set)
    for docid in docids:
        try:
            fname, lineno_str = docid.split(':', 1)
            lineno = int(lineno_str)
            if lineno > 0:
                grouped_by_file[fname].add(lineno)
            else:
                logging.warning(f"[get_memories] Invalid line number in docid: {docid}")
        except (ValueError, IndexError) as e:
            logging.warning(f"[get_memories] Could not parse docid '{docid}': {e}")
            continue

    # Dictionary to store results mapped by original docid
    results_map = {}

    # Process each file that contains needed lines
    for fname, lines_to_read_set in grouped_by_file.items():
        path = JSONL_DIR / fname
        if not path.exists():
            logging.warning(f"[get_memories] Memory file referenced in docid not found: {fname}")
            # Mark all docids associated with this file as un-retrievable
            for lineno in lines_to_read_set:
                 missing_docid = f"{fname}:{lineno}"
                 if missing_docid in docids: # Check if this specific docid was requested
                     results_map[missing_docid] = None # Indicate failure to retrieve
            continue

        logging.debug(f"[get_memories] Reading file: {fname} to retrieve lines: {lines_to_read_set}")
        try:
            # Read all lines into memory for this file
            with open(path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
            
            file_line_count = len(all_lines)

            # Access specific lines
            for lineno in lines_to_read_set:
                current_docid = f"{fname}:{lineno}"
                if lineno > file_line_count:
                    logging.warning(f"[get_memories] Line number {lineno} exceeds file length ({file_line_count}) for {fname}. Docid: {current_docid}")
                    results_map[current_docid] = None # Mark as failed
                    continue
                
                try:
                    # Access line using 0-based index
                    line_content = all_lines[lineno - 1].strip()
                    logging.debug(f"[get_memories] Content for {current_docid}: '{line_content[:100]}...'")
                    if line_content:
                        parsed_record = json.loads(line_content)
                        results_map[current_docid] = parsed_record
                        logging.debug(f"[get_memories] Stored record for {current_docid}")
                    else:
                        logging.warning(f"[get_memories] Requested line {lineno} in {fname} was empty. Docid: {current_docid}")
                        results_map[current_docid] = None # Mark as failed (empty line)
                        
                except json.JSONDecodeError:
                    logging.warning(f"[get_memories] Failed to decode JSON for {current_docid}: {line_content[:100]}...")
                    results_map[current_docid] = None # Mark as failed
                except Exception as parse_err:
                    logging.error(f"[get_memories] Error processing {current_docid}: {parse_err}")
                    results_map[current_docid] = None # Mark as failed

        except Exception as e:
            logging.error(f"[get_memories] Error reading file {fname}: {e}")
            # Mark all docids associated with this file as un-retrievable if file read fails
            for lineno in lines_to_read_set:
                 missing_docid = f"{fname}:{lineno}"
                 if missing_docid in docids:
                     results_map[missing_docid] = None
            continue

    # Construct final list preserving the order from the original FTS query (docids list)
    final_results = []
    retrieved_count = 0
    logging.debug(f"[get_memories] Reconstructing final list from {len(docids)} input docids...")
    # No need to log results_map keys again, was added previously
    for docid in docids:
        logging.debug(f"[get_memories] Checking input docid: {docid}")
        retrieved_record = results_map.get(docid)
        if retrieved_record is not None:
            logging.debug(f"[get_memories]   Found in results_map. Appending.")
            final_results.append(retrieved_record)
            retrieved_count += 1
        else:
             # Log if a docid from FTS query couldn't be retrieved or failed processing
             logging.warning(f"[get_memories] Could not retrieve/process record for docid {docid} found in FTS index.")
             
    logging.info(f"Successfully retrieved {retrieved_count} full memory records for {len(docids)} docids requested by FTS.")
    return final_results

# --- End FTS5 Integration ---

# --- Save Memory --- 
def save_memory(event_type, details):
    """Saves a memory event to a date-stamped JSON Lines file and updates FTS index."""
    record = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "details": details # Assumes details is already JSON-serializable (e.g., dict, string)
    }
    filename_str = f"{datetime.now().strftime('%Y%m%d')}_memory.jsonl"
    filepath = JSONL_DIR / filename_str # Use Path object
    
    line_no = -1 # Initialize line number
    try:
        # --- Append to JSONL ---
        try:
            # Validate and serialize the record to a JSON string
            json_line = json.dumps(record, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            logging.error(f"Failed to JSON-serialize memory record: {e} | record={record!r}")
            # Optional: Re-raise if saving is critical, or return to skip FTS indexing for this record
            return # Skip writing corrupted record and subsequent FTS indexing

        # Ensure the directory exists (redundant if JSONL_DIR is always valid, but safe)
        JSONL_DIR.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'a', encoding='utf-8') as f:
            # Get current position to check if file is empty/needs newline
            f.seek(0, os.SEEK_END)
            is_empty = f.tell() == 0
            # Construct the prefix (newline or empty string)
            prefix = '\n' if not is_empty else ''
            # Write the prefix and the JSON string
            f.write(f"{prefix}{json_line}")

        # Estimate line number based on newlines - THIS IS NOT ROBUST
        # A better way is needed if exact line number is critical
        # For now, we re-read after writing. Consider passing line count if known.
        logging.debug(f"Saved memory event '{event_type}' to {filepath}")

        # --- NEW: Incremental FTS5 Index Update ---
        # Determine line number accurately *after* writing
        try:
            with open(filepath, 'r', encoding='utf-8') as f_check:
                 # This counts lines accurately but reads the whole file
                 line_no = sum(1 for line in f_check if line.strip())
        except Exception as count_e:
             logging.error(f"Could not count lines in {filepath} to determine docid: {count_e}")
             raise count_e # Re-raise to indicate failure

        docid = f"{filepath.name}:{line_no}" # Use filename:line_number
        ts = record["timestamp"]
        et = record["event_type"]
        # Use JSON for dict details, or str() otherwise
        content = json.dumps(details, sort_keys=True) if isinstance(details, dict) else str(details)

        conn_fts = None # Use a different var name to avoid scope issues
        try:
            # Insert into FTS table
            conn_fts = sqlite3.connect(DB_PATH)
            # Use INSERT OR IGNORE to handle potential duplicate docids if logic isn't perfect
            conn_fts.execute(
                "INSERT OR IGNORE INTO memory_fts (docid, timestamp, event_type, content) VALUES (?,?,?,?);",
                (docid, ts, et, content)
            )
            conn_fts.commit()
            logging.debug(f"Updated FTS index for docid {docid}")
        except sqlite3.Error as fts_e:
            logging.error(f"Failed to update FTS index for memory {docid}: {fts_e}")
            # Don't halt execution, just log the FTS failure
        except Exception as e:
            logging.error(f"Unexpected error updating FTS index for memory {docid}: {e}")
        finally:
            if conn_fts:
                conn_fts.close()
                
    except Exception as e:
        # This catches errors during JSONL write or line counting
        logging.error(f"Failed to save memory or update FTS index: {e}", exc_info=True)

# --- Retrieve Memory --- 
def retrieve_memory(event_type=None, limit=None):
    """
    Retrieves memory events from JSON Lines files.
    Can filter by event_type and limit results.
    Returns a list of memory record dictionaries.
    Note: Simple implementation loads all relevant files for now.
    """
    memories = []
    logging.debug(f"Retrieving memories (event_type={event_type}, limit={limit})")
    try:
        # Sort files potentially by date if needed, though loading all is simple for now
        memory_files = sorted([f for f in os.listdir(MEMORY_DIR) if f.endswith(".jsonl")], reverse=True)
        
        for filename in memory_files:
            filepath = os.path.join(MEMORY_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            record = json.loads(line)
                            # Apply filtering
                            if event_type is None or record.get('event_type') == event_type:
                                memories.append(record)
                                # Apply limit if specified
                                if limit is not None and len(memories) >= limit:
                                    break # Stop reading this file
                        except json.JSONDecodeError:
                            logging.warning(f"Skipping corrupted line in {filename}: {line.strip()}")
                        except Exception as parse_e:
                             logging.warning(f"Error processing record from {filename}: {parse_e}")
            except Exception as file_e:
                logging.error(f"Error reading memory file {filepath}: {file_e}")
            
            # Stop reading older files if limit is reached
            if limit is not None and len(memories) >= limit:
                break
                
    except FileNotFoundError:
        logging.info(f"Memory storage directory {MEMORY_DIR} not found during retrieval.")
        return [] # Return empty list if directory doesn't exist
    except Exception as e:
        logging.error(f"General error during memory retrieval: {e}", exc_info=True)
        return [] # Return empty on other errors
        
    logging.debug(f"Retrieved {len(memories)} memory events.")
    # Return memories potentially sorted chronologically (newest first due to file order)
    return memories

# --- Compatibility Shim --- 
# This function exists to match the previous call signature used in memory_query
# It retrieves memories and returns the details field, mimicking the old structure.
def retrieve_memory_compat(event_type=None):
    """Retrieves memories and returns details field for compatibility."""
    records = retrieve_memory(event_type=event_type)
    # Return list of (id_placeholder, timestamp, event_type, details)
    # Using timestamp as a pseudo-ID for now
    return [(r.get('timestamp'), r.get('timestamp'), r.get('event_type'), r.get('details')) for r in records]

# Example Usage (if running manually)
if __name__ == "__main__":
    print("Testing Simple JSONL Memory Engine...")
    save_memory("test_event", {"data": "value1", "count": 1})
    save_memory("test_event", {"data": "value2", "count": 2})
    save_memory("other_event", {"info": "some info"})
    
    print("\nRetrieving all memories:")
    all_mem = retrieve_memory()
    print(json.dumps(all_mem, indent=2))
    
    print("\nRetrieving only 'test_event' memories (limit 1):")
    test_mem = retrieve_memory(event_type="test_event", limit=1)
    print(json.dumps(test_mem, indent=2))

    print("\nRetrieving via compatibility shim:")
    compat_mem = retrieve_memory_compat(event_type="test_event")
    print(compat_mem) # Prints list of tuples 