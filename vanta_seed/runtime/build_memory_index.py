# vanta_seed/runtime/build_memory_index.py
"""
Script to build (or rebuild) the SQLite FTS5 index for VANTA-SEED memories.
Reads from JSONL files and populates the memory_index.db.
"""

import os
import json
import sqlite3
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define paths relative to this script's location
SCRIPT_DIR = Path(__file__).parent
VANTA_SEED_DIR = SCRIPT_DIR.parent
MEMORY_STORAGE_DIR = VANTA_SEED_DIR / 'memory_storage'
DB_PATH = MEMORY_STORAGE_DIR / 'memory_index.db'

def build_index():
    """Builds the FTS5 index from JSONL files."""
    logger.info(f"Starting FTS index build. Database path: {DB_PATH}")
    
    conn = None
    try:
        # Ensure storage directory exists
        MEMORY_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        logger.info("Dropping existing FTS table (if any)...")
        cursor.execute('''DROP TABLE IF EXISTS memory_fts;''')
        
        logger.info("Creating new FTS5 table 'memory_fts'...")
        # Using the schema from the sketch
        cursor.execute("""
          CREATE VIRTUAL TABLE memory_fts
          USING fts5(
              docid UNINDEXED,          -- e.g. '20250426_memory.jsonl:123'
              timestamp UNINDEXED,      -- ISO8601 string
              event_type UNINDEXED,     -- categorical filter
              content                   -- FTS-indexed JSON details or synthesized text
          );
        """)
        
        jsonl_files = list(MEMORY_STORAGE_DIR.glob('*.jsonl'))
        if not jsonl_files:
            logger.warning(f"No *.jsonl memory files found in {MEMORY_STORAGE_DIR}. Index will be empty.")
            return

        logger.info(f"Found {len(jsonl_files)} JSONL file(s) to process.")
        total_records_processed = 0
        total_records_inserted = 0

        for filepath in jsonl_files:
            logger.info(f"Processing file: {filepath.name}...")
            records_in_file = 0
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f, start=1):
                        total_records_processed += 1
                        records_in_file += 1
                        try:
                            if not line.strip(): continue # Skip empty lines
                            rec = json.loads(line)
                            
                            # --- Data Extraction and Preparation ---
                            docid = f"{filepath.name}:{i}"
                            ts = rec.get('timestamp','')
                            et = rec.get('event_type','')
                            
                            # Prioritize 'details' for content, fallback to 'content'
                            details_content = rec.get('details')
                            if details_content is None:
                                details_content = rec.get('content', '') # Fallback
                                
                            # Serialize if dict, otherwise use string representation
                            if isinstance(details_content, dict):
                                content_for_fts = json.dumps(details_content, sort_keys=True)
                            else:
                                content_for_fts = str(details_content)
                            # --- End Data Extraction ---

                            # Basic validation
                            if not ts or not et:
                                logger.warning(f"Skipping line {i} in {filepath.name}: Missing timestamp or event_type.")
                                continue
                                
                            cursor.execute("INSERT INTO memory_fts (docid, timestamp, event_type, content) VALUES (?, ?, ?, ?)", 
                                           (docid, ts, et, content_for_fts))
                            total_records_inserted += 1
                            
                        except json.JSONDecodeError:
                            logger.warning(f"Skipping line {i} in {filepath.name}: Invalid JSON.")
                        except Exception as e:
                            logger.error(f"Error processing line {i} in {filepath.name}: {e}")
                            
            except Exception as e:
                logger.error(f"Error reading file {filepath.name}: {e}")
                
            logger.info(f"Finished processing {filepath.name} ({records_in_file} lines).")

        logger.info("Committing changes to the database...")
        conn.commit()
        logger.info(f"Index build complete. Total records processed: {total_records_processed}, Total records inserted: {total_records_inserted}")

    except sqlite3.Error as e:
        logger.error(f"SQLite error during index build: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
    finally:
        if conn:
            logger.info("Closing database connection.")
            conn.close()

if __name__=='__main__':
    build_index() 