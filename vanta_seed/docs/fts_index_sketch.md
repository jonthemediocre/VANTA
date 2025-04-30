# FTS Index Sketch for VANTA-SEED Memory

This document outlines a plan to integrate SQLite FTS5 into VANTA-SEED's memory system, enabling fast, sub-linear full-text search over the episodic JSONL memory store.

### 1. Database/Table Schema

We will create an FTS5 virtual table named `memory_fts` within a SQLite file: `vanta_seed/memory_storage/memory_index.db`.

**Schema:**

```sql
-- Create the FTS5 table mapping to JSONL entries
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts
USING fts5(
  docid TEXT UNINDEXED,         -- Unique identifier (e.g., 'filename:line_number')
  timestamp TEXT UNINDEXED,     -- ISO timestamp for audit/filtering
  event_type TEXT UNINDEXED,    -- e.g. "simulation_interaction", "breath_expansion_ritual"
  content TEXT                  -- Full-text indexed details (JSON-serialized 'details' or primary content)
  -- Add more UNINDEXED columns if needed for filtering without full retrieval
);
```

- **`docid`**: A stable identifier linking back to the source JSONL entry. Recommended format: `filename:line_number` (e.g., `20250426_memory.jsonl:15`). This assumes JSONL files are append-only and not heavily modified.
- **`timestamp`**: Stored for potential time-based filtering (though FTS itself doesn't optimize date range queries well).
- **`event_type`**: Allows basic filtering by the type of memory event.
- **`content`**: The primary column for FTS indexing. This will store the serialized JSON `details` field, or the primary `content` field if `details` isn't present/applicable in the source memory record.

### 2. Indexing Process

#### a. Initial / Batch Index Build

- A dedicated script `vanta_seed/runtime/build_memory_index.py` will be created.
- **Functionality:**
    1. Connects to `vanta_seed/memory_storage/memory_index.db` (creates if not exists).
    2. Drops and recreates the `memory_fts` table to ensure a clean index.
    3. Iterates through all `*.jsonl` files in `vanta_seed/memory_storage/`.
    4. For each line (memory record):
        - Parses the JSON.
        - Validates required fields (`timestamp`, `event_type`, `content`/`details`).
        - Constructs the `docid` (e.g., `f"{os.path.basename(filepath)}:{line_number}"`).
        - Extracts `timestamp` and `event_type`.
        - Serializes the `details` or gets the `content` string for the `content` column.
        - Inserts the data into the `memory_fts` table using parameter binding.
    5. Commits the transaction.
    6. Logs progress and completion.

#### b. Incremental Updates (On Write)

- Modify `vanta_seed/memory/memory_engine.save_memory()`:
    1. After successfully appending the `memory_dict` to the JSONL file:
    2. Determine the `filename` and `line_number` for the newly appended record (this might require reading the file length before appending or tracking internally).
    3. Construct the `docid`.
    4. Extract `timestamp`, `event_type`, and the `content`/`details` string.
    5. Connect to `memory_index.db`.
    6. Execute an `INSERT` statement for the `memory_fts` table with the new record's data. Use appropriate error handling (`try...except sqlite3.Error`).
    7. Commit the transaction and close the connection.

- **Duplicate Handling:** The batch build starts fresh. The incremental update assumes new writes are unique; if re-indexing existing data is a possibility, `INSERT OR IGNORE` or `INSERT OR REPLACE` (based on `docid`) could be used, but might add overhead.

### 3. Query Interface

- Add a new function to `vanta_seed/memory/memory_engine.py` (or a dedicated `memory_query_fts.py`).

```python
# In memory_engine.py or similar
import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parents[1] / 'memory_storage' / 'memory_index.db'

def query_memory_fts(search_term: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Perform FTS search and return full original memory records.
    """
    if not DB_PATH.exists():
        logger.warning(f"FTS index database not found at {DB_PATH}. Cannot perform FTS query.")
        return []
        
    results = []
    matched_docids = []
    conn = None  # Initialize conn to None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row # Optional: access columns by name

        # Use FTS MATCH syntax - consider adding ranking or specific column queries later
        # Example: 'content MATCH ?' or 'memory_fts MATCH ?' (searches all indexed cols)
        sql = '''
        SELECT docid, timestamp, event_type -- Select minimal fields needed
        FROM memory_fts
        WHERE content MATCH ? 
        ORDER BY rank -- Default ranking by relevance
        LIMIT ?;
        '''
        # FTS5 requires the search term directly, no wildcards needed unless using advanced syntax
        # Simple term matching is default. Use "" for phrases, AND/OR/NOT for boolean.
        
        cursor = conn.execute(sql, (search_term, limit))
        matched_docids = [row['docid'] for row in cursor.fetchall()]

    except sqlite3.Error as e:
        logger.error(f"FTS query failed: {e}")
        return [] # Return empty on error
    finally:
        if conn:
            conn.close()

    if not matched_docids:
        return [] # No matches found

    # Retrieve full records from JSONL based on docids
    full_results = get_memories_by_docids(matched_docids)
    return full_results

def get_memories_by_docids(docids: List[str]) -> List[Dict[str, Any]]:
    """
    Retrieve full memory records from JSONL files using docid (filename:linenum).
    (This function needs to be implemented)
    """
    logger.info(f"Retrieving full records for {len(docids)} matched docids...")
    # Implementation needed:
    # 1. Group docids by filename.
    # 2. For each file, open it and read the specific lines indicated by line numbers.
    # 3. Parse the JSON from those lines.
    # 4. Handle errors (file not found, line not found, JSON decode error).
    # 5. Return the list of parsed memory dictionaries.
    # Placeholder:
    retrieved_memories = [] 
    # ... implementation logic ...
    logger.warning("Placeholder: get_memories_by_docids needs implementation!")
    return retrieved_memories 

```

- **Query Syntax:** Basic term matching. Advanced FTS5 syntax (phrases, boolean operators) can be used if needed by modifying how `search_term` is formatted for the `MATCH ?` placeholder.
- **Retrieval:** The query gets matching `docid`s, then a helper function (`get_memories_by_docids`) retrieves the full records from the JSONL files.

### 4. Integration Strategy

- **Primary Query Path:** For user-facing queries or internal lookups needing speed, attempt `query_memory_fts` first.
- **Fallback:** If FTS query fails or returns no results (and a broader search is desired), fall back to existing methods like `load_all_memories` + filtering or Fractal Map queries.
- **Fractal Linking:** The `create_fractal_links` process will likely continue using `load_all_memories` as it needs the complete dataset to build constellations.

### 5. Dependencies

- **`sqlite3`**: Included in Python standard library. No external dependencies needed for this core functionality.

---

This approach provides a significant performance boost for text-based memory retrieval with minimal added complexity or external dependencies, complementing the existing JSONL audit trail and the symbolic Fractal Map. 