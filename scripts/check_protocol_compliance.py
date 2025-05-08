"""
Protocol Compliance Checker for VANTA Kernel

This script cross-validates trigger_registry.py, roles.yaml (or caregiver_roles.yaml),
and potentially vanta_trigger_engine.py for compliance.
"""
import sys
import os
import importlib
import logging
import utils # Import the new utility module

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - COMPLIANCE - %(levelname)s - %(message)s')

# Constants are now primarily managed in utils.py, but keep local reference if needed
TRIGGER_ENGINE_PATH = "vanta_trigger_engine.py"


def check_module_exists(module_name):
    # Small helper, might move to utils if used elsewhere
    try:
        # Validate module name format briefly
        if not module_name or not isinstance(module_name, str) or '.' not in module_name:
             logging.warning(f"Potentially invalid module name format: {module_name}")
             # Depending on strictness, could return False here
             # return False
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False
    except Exception as e:
        logging.error(f"Unexpected error checking module {module_name}: {e}")
        return False

def main():
    errors = []
    warnings = []
    script_name = os.path.basename(__file__)

    # --- Load Data using Utils --- 
    logging.info("Loading data using utility functions...")
    triggers = utils.load_trigger_registry()
    roles_data = utils.load_caregiver_roles()
    
    # Handle loading failures
    if triggers is None:
        errors.append(f"[ERROR] Failed to load trigger registry. Cannot perform checks.")
    if roles_data is None:
        # load_caregiver_roles returns None if file not found, {} if empty
        warnings.append(f"[WARN] No roles file found or file is invalid (checked: {utils.ROLES_PATHS}). Role checks will be skipped or may produce errors.")
        defined_roles = set() # Assume no roles defined if file is missing/invalid
    else:
        defined_roles = set(roles_data.keys())
        if not defined_roles:
            warnings.append(f"[WARN] Roles file loaded but contains no defined roles.")

    # Exit early if trigger registry failed to load
    if triggers is None:
        print("[ERROR] Cannot proceed without trigger registry.")
        print(f"VANTA_COMPLIANCE_CHECK_FAILED: {script_name} - {len(errors)} error(s) found.")
        sys.exit(1)
        
    logging.info("Data loading complete. Starting compliance checks...")
    # --- Perform Checks --- 

    # Check trigger modules and roles
    for trig in triggers:
        module_name = trig.get("module")
        trigger_id = trig.get("id", "(unknown ID)")
        contexts = trig.get("contexts", [])
        protocol = trig.get("protocol") # Added protocol check

        # Check module existence
        if module_name:
            if not check_module_exists(module_name):
                errors.append(f"[ERROR] Trigger '{trigger_id}' references missing or invalid module: {module_name}")
        else:
            warnings.append(f"[WARN] Trigger '{trigger_id}' does not define a 'module'.")
             
        # Check contexts against defined roles
        if contexts: # Only check if contexts are specified
            if roles_data is None: # Roles file was missing/invalid
                 warnings.append(f"[WARN] Trigger '{trigger_id}' defines contexts {contexts}, but roles file was not loaded. Cannot validate roles.")
            else: # Roles file was loaded (might be empty)
                for ctx in contexts:
                    if ctx not in defined_roles:
                        errors.append(f"[ERROR] Trigger '{trigger_id}' references undefined role/context: '{ctx}'. Defined roles: {list(defined_roles)}")
        # else: # No contexts specified - potentially global trigger?
        #     warnings.append(f"[WARN] Trigger '{trigger_id}' does not define any 'contexts'. Assuming global applicability.")
        
        # Check if protocol is defined
        if not protocol:
             warnings.append(f"[WARN] Trigger '{trigger_id}' does not define a 'protocol'.")

    # Check for unused roles
    if roles_data is not None and defined_roles: # Only if roles were loaded and not empty
        used_roles = {ctx for trig in triggers for ctx in trig.get("contexts", []) if trig.get("contexts")}
        unused_roles = defined_roles - used_roles
        for role in unused_roles:
            warnings.append(f"[WARN] Role/context '{role}' defined but not used in any trigger context.")

    # Check for protocol implementation hint in vanta_trigger_engine.py
    if os.path.exists(TRIGGER_ENGINE_PATH):
        try:
            with open(TRIGGER_ENGINE_PATH, "r", encoding='utf-8') as f:
                engine_code = f.read()
            defined_protocols = {trig.get("protocol") for trig in triggers if trig.get("protocol")}
            for protocol_name in defined_protocols:
                 # Very basic check: does the protocol name appear as likely text?
                 # A more robust check might look for specific function/class definitions.
                if protocol_name not in engine_code:
                     warnings.append(f"[WARN] Protocol '{protocol_name}' (defined in registry) potentially not handled in {TRIGGER_ENGINE_PATH} (simple text check).")
        except Exception as e:
            # Changed from error to warning as this is just a hint
            warnings.append(f"[WARN] Could not read or parse {TRIGGER_ENGINE_PATH} for protocol check: {e}") 
    else:
        # Changed from error to warning as engine might not be needed for *just* registry checks
        warnings.append(f"[WARN] {TRIGGER_ENGINE_PATH} not found. Cannot check for protocol implementation hints.")

    # --- Output results --- 
    logging.info("Compliance checks finished. Aggregating results...")
    # Print warnings first
    for warn_msg in warnings:
        print(warn_msg)
    # Print errors next
    for err_msg in errors:
        print(err_msg) # Could also use sys.stderr.write(f"{err_msg}\n")

    # Print final summary line and set exit code (Rule 913)
    if errors:
        print(f"VANTA_COMPLIANCE_CHECK_FAILED: {script_name} - {len(errors)} error(s) found.")
        sys.exit(1)
    elif warnings:
        print(f"VANTA_COMPLIANCE_CHECK_PASSED_WITH_WARNINGS: {script_name} - Checks passed with {len(warnings)} warning(s).")
        sys.exit(0)
    else:
        print(f"VANTA_COMPLIANCE_CHECK_PASSED: {script_name} - All checks passed.")
        sys.exit(0)

if __name__ == "__main__":
    # Ensure PYTHONPATH includes project root when running directly
    # Example: PYTHONPATH=. python scripts/check_protocol_compliance.py
    main() 