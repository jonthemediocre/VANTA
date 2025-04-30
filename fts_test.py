# fts_test.py
# Temporary script to test FTS5 integration

import json
import logging
import sys
import os

# Adjust path to import from vanta_seed (assuming script is run from VANTA root)
# This ensures the script can find the vanta_seed package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '')))

try:
    from vanta_seed.memory.memory_engine import save_memory, query_memory_fts
except ImportError as e:
    print(f"ERROR: Could not import from vanta_seed.memory.memory_engine: {e}")
    print("Ensure this script is run from the VANTA project root directory (the one containing vanta_seed).")
    sys.exit(1)

# Configure basic logging for the test
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - TEST_FTS - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_tests():
    logger.info("--- Starting FTS Integration Test ---")
    passed_tests = 0
    total_tests = 3

    # === Test 1: Initial Save & Query ===
    logger.info("Running Test 1: Initial Save & Query...")
    test_detail_1 = {"foo": "bar", "note": "FTS index test 1"}
    test_passed_1 = False
    try:
        save_memory("test_event", test_detail_1)
        logger.info("Test record 1 saved.")
        results1 = query_memory_fts("foo") # Query for term in details
        logger.info(f"FTS query for 'foo' executed. Found {len(results1)} result(s).")
        print("\n--- Test 1 Results ---")
        print(json.dumps(results1, indent=2))
        # Verification: Check if at least one result matches
        for res in results1:
            if isinstance(res.get('details'), dict) and res['details'].get('foo') == 'bar':
                test_passed_1 = True
                break
        if test_passed_1:
            logger.info("[SUCCESS] Test 1: Record found via FTS.")
            passed_tests += 1
        else:
            logger.error("[FAILURE] Test 1: Correct record not found via FTS.")

    except Exception as e:
        logger.error(f"[FAILURE] Test 1 encountered an error: {e}", exc_info=True)

    # === Test 2: Duplicate Handling Check ===
    # We expect a new entry because line number changes, making docid unique.
    # This tests if INSERT OR IGNORE prevents errors, not logical duplication.
    logger.info("\nRunning Test 2: Duplicate Content Save Attempt...")
    test_detail_2 = {"foo": "bar", "note": "FTS index test 2 (duplicate content attempt)"}
    test_passed_2 = False
    try:
        save_memory("test_event", test_detail_2) # Save again with same content type
        logger.info("Test record 2 (duplicate content) saved.")
        results2 = query_memory_fts("foo")
        logger.info(f"FTS query for 'foo' executed after second save. Found {len(results2)} result(s).")
        print("\n--- Test 2 Results (After Duplicate Content Save) ---")
        print(json.dumps(results2, indent=2))
        # Verification: Expect more than one result now
        if len(results2) > len(results1 if 'results1' in locals() else []):
             logger.info("[SUCCESS] Test 2: Second save created a new index entry as expected (docid changed).")
             test_passed_2 = True
             passed_tests +=1
        else:
             logger.error("[FAILURE] Test 2: Second save did not appear to add a new entry.")

    except Exception as e:
        logger.error(f"[FAILURE] Test 2 encountered an error: {e}", exc_info=True)


    # === Test 3: Edge Case (String Detail) ===
    logger.info("\nRunning Test 3: String Detail Save & Query...")
    test_detail_3 = "quick brown fox jumps"
    test_passed_3 = False
    try:
        save_memory("test_text", test_detail_3)
        logger.info("Test record 3 (string detail) saved.")
        results3 = query_memory_fts("brown") # Query for term within the string
        logger.info(f"FTS query for 'brown' executed. Found {len(results3)} result(s).")
        print("\n--- Test 3 Results (String Detail) ---")
        print(json.dumps(results3, indent=2))
        # Verification: Check if at least one result matches
        for res in results3:
             if res.get('event_type') == 'test_text' and res.get('details') == test_detail_3:
                  test_passed_3 = True
                  break
        if test_passed_3:
            logger.info("[SUCCESS] Test 3: String detail record found via FTS.")
            passed_tests += 1
        else:
            logger.error("[FAILURE] Test 3: String detail record not found.")

    except Exception as e:
        logger.error(f"[FAILURE] Test 3 encountered an error: {e}", exc_info=True)

    # --- Summary ---
    logger.info(f"\n--- Test Summary: {passed_tests} / {total_tests} Passed ---")

if __name__ == "__main__":
    run_tests() 