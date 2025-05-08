import os
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, TypedDict, Union

# Assuming BaseAgent will be available from this path
from vanta_seed.core.base_agent import BaseAgent # Corrected Import

# --- Constants for Detection Logic ---
FAILURE_THRESHOLD = 3  # Number of failures/no_changes to trigger a report
RECENT_LOG_WINDOW_SIZE = 100  # Max number of recent log entries to keep in memory for pattern matching
CONFLICT_TIME_WINDOW_SECONDS = 300  # Time window (5 minutes) to detect conflicting successful edits on the same file
EDIT_TOOL_NAMES = [
    "edit_file", # default_api
    "mcp_desktop-commander_edit_block",
    "mcp_desktop-commander_write_file"
]

# --- TypedDict for structured reports ---
class IncoherenceReport(TypedDict):
    report_id: str
    issue_type: str  # e.g., "repeated_failure", "conflicting_edit", "no_changes_loop"
    description: str
    affected_files: List[str]
    involved_agents: List[str]
    log_entry_ids: List[str] # References to problematic log_id
    severity: str # "LOW", "MEDIUM", "HIGH"
    timestamp: str
    suggested_action: Optional[str]

# Correct inheritance
class IncoherenceDetectionAgent(BaseAgent):
    def __init__(self, agent_id: str = "incoherence_detector", core: Optional[Any] = None):
        super().__init__(agent_id, core)
        # self.agent_id is set by BaseAgent
        # self.core is set by BaseAgent
        # self.logger setup needs to be confirmed based on BaseAgent implementation
        # Assuming BaseAgent provides self.logger or a way to get it from core
        if not hasattr(self, 'logger'): # Basic check if logger was setup by BaseAgent
             self.logger = core.get_logger(agent_id) if core and hasattr(core, 'get_logger') else print
             if not (core and hasattr(core, 'get_logger')):
                 self.logger = lambda *args, **kwargs: print(f"[{self.agent_id}]", *args, **kwargs) # Fallback print logger

        self.monitored_files_config = [ # From MDC 006
            "run.py",
            "vanta_seed/core/vanta_master_core.py",
            "blueprint.yaml",
            ".cursor/rules/**/*.mdc", # This is a glob, needs careful handling if used directly
            "agent_cascade_definitions.mdc",
            "THEPLAN.md"
        ]
        # Actual path determined by core or config
        self.log_file_path = self.core.config.get("agent_replay_log_path", "logs/agentic_replay.log.jsonl") if self.core and hasattr(self.core, 'config') else "logs/agentic_replay.log.jsonl"
        self.logger(f"Initialized. Monitoring log: {self.log_file_path}")

    async def process_input(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        command = data.get("command")
        if command == "check_system_incoherence":
            target_file = data.get("target_file")
            self.logger(f"Received command: {command}, target: {target_file}")
            return await self.perform_incoherence_check(target_file)

        self.logger(f"Unknown command: {command}")
        return {"status": "error", "message": f"Unknown command: {command}"}

    async def perform_incoherence_check(self, target_file: Optional[str] = None) -> Dict[str, Any]:
        self.logger(f"Performing incoherence check. Target: {target_file if target_file else 'all monitored'}")

        if not os.path.exists(self.log_file_path):
            self.logger(f"Warning: Log file not found at {self.log_file_path}. Cannot perform analysis.")
            return {"status": "no_logs_found", "message": f"Log file {self.log_file_path} not found."}

        reports: List[IncoherenceReport] = await self._analyze_agent_logs(target_file)

        if reports:
            self.logger(f"Incoherence detected. Reports: {reports}")
            if self.core and hasattr(self.core, 'emit_mcp_signal'):
                self.core.emit_mcp_signal(
                    "system_incoherence_detected",
                    {
                        "findings": reports,
                        "resolution_protocol_version": "006_v1", # From MDC 006
                        "agent_id": self.agent_id
                    }
                )
            return {"status": "incoherence_detected", "details": reports}

        self.logger("No incoherence patterns detected based on current heuristics.")
        return {"status": "no_incoherence_detected", "details": "Analysis complete, no specific incoherence patterns found."}

    def _parse_log_entry(self, line_number: int, log_line: str) -> Optional[Dict[str, Any]]:
        try:
            entry = json.loads(log_line)
            # Basic validation based on schema's required fields
            required_fields = ["log_id", "timestamp", "agent_id", "action_type", "status"]
            if not all(field in entry for field in required_fields):
                self.logger(f"Warning: Malformed log entry at line {line_number}. Missing required fields. Entry: {log_line[:200]}...")
                return None

            # Attempt to parse timestamp for time-based comparisons
            try:
                entry['parsed_timestamp'] = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
            except ValueError:
                self.logger(f"Warning: Could not parse timestamp for log_id {entry.get('log_id', 'UNKNOWN')} at line {line_number}. Timestamp: {entry.get('timestamp')}")
                entry['parsed_timestamp'] = datetime.now(timezone.utc) # Fallback, though not ideal
            return entry
        except json.JSONDecodeError:
            self.logger(f"Warning: Could not parse JSON from log line {line_number}: {log_line[:200]}...")
            return None

    def _is_edit_action(self, entry: Dict[str, Any]) -> bool:
        return entry.get("action_type") == "TOOL_CALL_RESULT" and \
               entry.get("tool_name") in EDIT_TOOL_NAMES

    def _get_target_file_from_entry(self, entry: Dict[str, Any]) -> Optional[str]:
        params = entry.get("parameters")
        if isinstance(params, dict):
            return params.get("target_file")
        return None

    async def _analyze_agent_logs(self, specific_target_file: Optional[str] = None) -> List[IncoherenceReport]:
        self.logger(f"Starting analysis of agent logs. Specific target: {specific_target_file}")
        reports: List[IncoherenceReport] = []

        # Store recent actions: key is (target_file, agent_id, tool_name), value is list of (timestamp, status, log_id)
        recent_file_actions: Dict[tuple, List[Dict[str, Any]]] = {} # Corrected type hint
        # Store successful edits: key is target_file, value is list of (timestamp, agent_id, log_id, params_summary)
        successful_edits: Dict[str, List[Dict[str, Any]]] = {}

        processed_lines = 0
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                for line_num, log_line in enumerate(f, 1):
                    processed_lines += 1
                    entry = self._parse_log_entry(line_num, log_line)
                    if not entry:
                        continue

                    log_id = entry["log_id"]
                    agent_id = entry["agent_id"]
                    action_type = entry["action_type"]
                    status = entry["status"]
                    tool_name = entry.get("tool_name")
                    timestamp = entry["parsed_timestamp"]
                    entry_target_file = self._get_target_file_from_entry(entry)

                    # Filter by specific_target_file if provided
                    if specific_target_file and entry_target_file != specific_target_file:
                        continue

                    # --- Heuristic 1: Repeated Failures or "No Changes" for edit tools ---
                    if self._is_edit_action(entry) and entry_target_file:
                        if status in ["FAILURE", "NO_CHANGES_REPORTED"]:
                            action_key = (entry_target_file, agent_id, tool_name)
                            if action_key not in recent_file_actions:
                                recent_file_actions[action_key] = []

                            # Add current failure/no_change
                            recent_file_actions[action_key].append({
                                "timestamp": timestamp,
                                "status": status,
                                "log_id": log_id
                            })

                            # Keep window size
                            recent_file_actions[action_key] = recent_file_actions[action_key][-RECENT_LOG_WINDOW_SIZE:]

                            # Check threshold
                            failures_or_no_changes = [
                                act for act in recent_file_actions[action_key]
                                if act["status"] in ["FAILURE", "NO_CHANGES_REPORTED"]
                            ]
                            if len(failures_or_no_changes) >= FAILURE_THRESHOLD:
                                report_exists = any(
                                    r["issue_type"] == "repeated_issue_on_file" and
                                    entry_target_file in r["affected_files"] and
                                    agent_id in r["involved_agents"] and
                                    r.get("action_key_tuple") == action_key # Avoid duplicates for the same pattern
                                    for r in reports
                                )
                                if not report_exists:
                                    report = IncoherenceReport(
                                        report_id=str(uuid.uuid4()),
                                        issue_type="repeated_issue_on_file",
                                        description=f"Agent '{agent_id}' had {len(failures_or_no_changes)} '{status}' events for tool '{tool_name}' on file '{entry_target_file}' in recent logs.",
                                        affected_files=[entry_target_file],
                                        involved_agents=[agent_id],
                                        log_entry_ids=[act["log_id"] for act in failures_or_no_changes],
                                        severity="MEDIUM",
                                        timestamp=datetime.now(timezone.utc).isoformat(),
                                        suggested_action=f"Review logs for agent {agent_id} operations on {entry_target_file}.",
                                        # Add custom key for duplicate check, not part of official TypedDict
                                        # action_key_tuple=action_key
                                    )
                                    reports.append(report)
                                    self.logger(f"ALERT: Repeated issue pattern detected for {action_key}")

                        elif status == "SUCCESS" and entry_target_file:
                            # Clear failure history for this specific key on success
                            action_key_success = (entry_target_file, agent_id, tool_name)
                            if action_key_success in recent_file_actions:
                                recent_file_actions[action_key_success] = [
                                    act for act in recent_file_actions[action_key_success] if act["status"] == "SUCCESS"
                                ]

                            # --- Heuristic 2: Conflicting Successful Edits ---
                            if entry_target_file not in successful_edits:
                                successful_edits[entry_target_file] = []

                            # Crude summary of parameters for comparison - can be improved
                            params_summary = json.dumps(entry.get("parameters", {}).get("code_edit", ""))[:50] \
                                if entry.get("parameters", {}).get("code_edit") \
                                else json.dumps(entry.get("parameters", {}).get("instructions", ""))[:50]

                            current_edit_info = {
                                "timestamp": timestamp,
                                "agent_id": agent_id,
                                "log_id": log_id,
                                "params_summary": params_summary,
                                "tool_name": tool_name
                            }

                            # Check against other recent successful edits on the same file
                            conflicting_pair_found = False
                            for prev_edit in successful_edits[entry_target_file]:
                                time_diff = abs((timestamp - prev_edit["timestamp"]).total_seconds())
                                # Check if different agents OR same agent but different tool (e.g., edit vs write)
                                is_different_agent_or_tool = agent_id != prev_edit["agent_id"] or tool_name != prev_edit["tool_name"]

                                if time_diff <= CONFLICT_TIME_WINDOW_SECONDS and is_different_agent_or_tool:
                                    # Different agents/tools editing same file in close succession
                                    pair_key = tuple(sorted([log_id, prev_edit["log_id"]])) # Key to prevent duplicate report for same pair
                                    report_exists = any(
                                        r["issue_type"] == "conflicting_successful_edits" and
                                        entry_target_file in r["affected_files"] and
                                        tuple(sorted(r["log_entry_ids"])) == pair_key
                                        for r in reports
                                    )
                                    if not report_exists:
                                        reports.append(IncoherenceReport(
                                            report_id=str(uuid.uuid4()),
                                            issue_type="conflicting_successful_edits",
                                            description=f"File '{entry_target_file}' successfully edited by agent '{prev_edit['agent_id']}' (tool: {prev_edit['tool_name']}, log: {prev_edit['log_id']}) and then by agent '{agent_id}' (tool: {tool_name}, log: {log_id}) within {int(time_diff)}s.",
                                            affected_files=[entry_target_file],
                                            involved_agents=list(set([prev_edit["agent_id"], agent_id])),
                                            log_entry_ids=[prev_edit["log_id"], log_id],
                                            severity="HIGH",
                                            timestamp=datetime.now(timezone.utc).isoformat(),
                                            suggested_action=f"Review edits on {entry_target_file} by agents {prev_edit['agent_id']} and {agent_id} for potential conflict (logs: {prev_edit['log_id']}, {log_id})."
                                        ))
                                        self.logger(f"ALERT: Conflicting successful edits detected on {entry_target_file} between logs {prev_edit['log_id']} and {log_id}")
                                        conflicting_pair_found = True
                                        break # Report once per conflicting pair found for the current edit

                            successful_edits[entry_target_file].append(current_edit_info)
                            # Keep window by time (more robust than count for this heuristic)
                            now_utc = datetime.now(timezone.utc)
                            cutoff_time = now_utc - timedelta(seconds=CONFLICT_TIME_WINDOW_SECONDS * 2) # Keep history slightly longer than window
                            successful_edits[entry_target_file] = [
                                e for e in successful_edits[entry_target_file]
                                if e["timestamp"] >= cutoff_time
                            ]

                    # TODO: Implement other heuristics from user directive:
                    # - "Multiple agents performing overlapping tasks" (more complex, needs task definition)
                    # - "Unexpected task chains" (requires understanding of expected chains/cascades)

                    if processed_lines % 1000 == 0: # Log progress for large files
                        self.logger(f"Processed {processed_lines} log entries...")

        except FileNotFoundError:
            self.logger(f"Error: Log file not found at {self.log_file_path} during analysis.")
        except Exception as e:
            self.logger(f"Error during log analysis at line ~{processed_lines}: {e}", exc_info=True)
            reports.append(IncoherenceReport( # Report analysis error itself
                report_id=str(uuid.uuid4()),
                issue_type="log_analysis_error",
                description=f"An error occurred during log file analysis near line {processed_lines}: {str(e)}",
                affected_files=[self.log_file_path],
                involved_agents=[self.agent_id],
                log_entry_ids=[],
                severity="HIGH",
                timestamp=datetime.now(timezone.utc).isoformat(),
                suggested_action="Check agent logs for IncoherenceDetectionAgent and the integrity of the replay log."
            ))

        self.logger(f"Log analysis complete. Found {len(reports)} potential incoherence reports.")
        # Clean up internal keys used for duplicate checking before returning
        for report in reports:
            if "action_key_tuple" in report:
                del report["action_key_tuple"]
        return reports

if __name__ == '__main__':
    import asyncio

    # --- Mock Core for standalone testing ---
    class MockCore:
        def __init__(self):
            self.config = {"agent_replay_log_path": "temp_agent_replay.log.jsonl"}
            self.log_entries_for_test = []

        def get_logger(self, agent_id_name):
            def logger(*args, **kwargs):
                print(f"[{agent_id_name}]", *args)
            return logger

        def emit_mcp_signal(self, signal_name, payload):
            print(f"[MockCore] MCP Signal Emitted: {signal_name}, Payload: {json.dumps(payload, indent=2)}") # Pretty print signal

        def create_temp_log_file(self, entries: List[Dict[str, Any]]):
            self.log_entries_for_test = entries
            # Ensure timestamps are strings
            for entry in entries:
                if isinstance(entry.get("timestamp"), datetime):
                     entry["timestamp"] = entry["timestamp"].isoformat()
            try:
                with open(self.config["agent_replay_log_path"], 'w', encoding='utf-8') as f:
                    for entry in entries:
                        # Ensure required fields are present before writing
                        entry.setdefault("log_id", str(uuid.uuid4()))
                        entry.setdefault("agent_id", "unknown_test_agent")
                        entry.setdefault("action_type", "UNKNOWN_TEST_ACTION")
                        entry.setdefault("status", "UNKNOWN_TEST_STATUS")
                        if "timestamp" not in entry:
                            entry["timestamp"] = datetime.now(timezone.utc).isoformat()

                        f.write(json.dumps(entry) + '\n')
                print(f"[MockCore] Created temp log file: {self.config['agent_replay_log_path']} with {len(entries)} entries.")
            except Exception as e:
                 print(f"[MockCore] Error creating temp log file: {e}")


        def cleanup_temp_log_file(self):
            if os.path.exists(self.config["agent_replay_log_path"]):
                try:
                    os.remove(self.config["agent_replay_log_path"])
                    print(f"[MockCore] Cleaned up temp log file: {self.config['agent_replay_log_path']}")
                except Exception as e:
                    print(f"[MockCore] Error cleaning up temp log file: {e}")


    mock_core_instance = MockCore()
    # Pass the mock core instance during agent initialization
    agent = IncoherenceDetectionAgent(core=mock_core_instance)

    async def test_agent():
        print("\n--- Testing IncoherenceDetectionAgent ---")

        # Example Log Entries
        log_time = datetime.now(timezone.utc)
        dummy_entries = [
            # Repeated failures on file1.py by agent_A
            {"timestamp": (log_time - timedelta(minutes=5)).isoformat(), "agent_id": "agent_A", "action_type": "TOOL_CALL_RESULT", "tool_name": "edit_file", "parameters": {"target_file": "file1.py"}, "status": "FAILURE", "result": {"message": "failed op1"}},
            {"timestamp": (log_time - timedelta(minutes=4)).isoformat(), "agent_id": "agent_A", "action_type": "TOOL_CALL_RESULT", "tool_name": "edit_file", "parameters": {"target_file": "file1.py"}, "status": "NO_CHANGES_REPORTED", "result": {"message": "no change op2"}},
            {"timestamp": (log_time - timedelta(minutes=3)).isoformat(), "agent_id": "agent_A", "action_type": "TOOL_CALL_RESULT", "tool_name": "edit_file", "parameters": {"target_file": "file1.py"}, "status": "FAILURE", "result": {"message": "failed op3"}}, # Should trigger report

            # Successful edit by agent_A on file2.py
            {"timestamp": (log_time - timedelta(minutes=2)).isoformat(), "agent_id": "agent_A", "action_type": "TOOL_CALL_RESULT", "tool_name": "edit_file", "parameters": {"target_file": "file2.py", "code_edit": "content A"}, "status": "SUCCESS", "result": {"message": "agent A edit"}},

            # Conflicting successful edit by agent_B on file2.py shortly after
            {"timestamp": (log_time - timedelta(minutes=1)).isoformat(), "agent_id": "agent_B", "action_type": "TOOL_CALL_RESULT", "tool_name": "mcp_desktop-commander_write_file", "parameters": {"target_file": "file2.py", "content": "content B"}, "status": "SUCCESS", "result": {"message": "agent B overwrite"}}, # Should trigger report

            # Non-conflicting edit on a different file
            {"timestamp": (log_time - timedelta(minutes=0.5)).isoformat(), "agent_id": "agent_C", "action_type": "TOOL_CALL_RESULT", "tool_name": "edit_file", "parameters": {"target_file": "file3.py", "code_edit": "content C"}, "status": "SUCCESS", "result": {"message": "agent C edit"}},
            # Edit on file2.py way before agent A, should not conflict
             {"timestamp": (log_time - timedelta(minutes=6)).isoformat(), "agent_id": "agent_D", "action_type": "TOOL_CALL_RESULT", "tool_name": "edit_file", "parameters": {"target_file": "file2.py"}, "status": "SUCCESS", "result": {"message": "agent D edit way before agent A"}},
            # Success clears failure count for agent_A on file1.py
            {"timestamp": (log_time - timedelta(minutes=2.5)).isoformat(), "agent_id": "agent_A", "action_type": "TOOL_CALL_RESULT", "tool_name": "edit_file", "parameters": {"target_file": "file1.py"}, "status": "SUCCESS", "result": {"message": "Success finally"}},
            # Failure again, but count reset
            {"timestamp": (log_time - timedelta(minutes=2)).isoformat(), "agent_id": "agent_A", "action_type": "TOOL_CALL_RESULT", "tool_name": "edit_file", "parameters": {"target_file": "file1.py"}, "status": "FAILURE", "result": {"message": "failed again"}},

        ]
        # Add required fields to dummy entries for testing standalone file creation
        for i, entry in enumerate(dummy_entries):
            entry["log_id"] = str(uuid.uuid4())
            entry["action_type"] = entry.get("action_type", "TOOL_CALL_RESULT")
            entry["status"] = entry.get("status", "UNKNOWN")


        mock_core_instance.create_temp_log_file(dummy_entries)

        # Test general check
        print("\n--- Performing general incoherence check ---")
        general_result = await agent.perform_incoherence_check()
        print(f"General check result: {json.dumps(general_result, indent=2)}")

        # Test specific file check
        print("\n--- Performing incoherence check for file1.py ---")
        specific_result_f1 = await agent.perform_incoherence_check(target_file="file1.py")
        print(f"Specific check result for file1.py: {json.dumps(specific_result_f1, indent=2)}")

        print("\n--- Performing incoherence check for file2.py ---")
        specific_result_f2 = await agent.perform_incoherence_check(target_file="file2.py")
        print(f"Specific check result for file2.py: {json.dumps(specific_result_f2, indent=2)}")

        mock_core_instance.cleanup_temp_log_file()
        print("\n--- Test Finished ---")

    asyncio.run(test_agent())
