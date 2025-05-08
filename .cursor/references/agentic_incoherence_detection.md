# Agentic Incoherence Detection Reference

## Overview

This document outlines conceptual workflows and considerations for cross-agent collaboration related to System Layer Incoherence (SLI) detection and resolution within the VANTA framework. The primary mechanism is the `IncoherenceDetectionAgent` and the associated `system_incoherence_detected_cascade`.

## Key Components

*   **MDC Rule**: `.cursor/rules/006-system-incoherence-protocol.mdc` (Defines SLI, triggers, heuristics, agent profile)
*   **Agent**: `vanta_seed/agents/system/incoherence_detection_agent.py` (Implements detection logic)
*   **Cascade**: `system_incoherence_detected_cascade` (Defined in `agent_cascade_definitions.mdc`) (Orchestrates response to detection)
*   **Ritual**: `.cursor/rituals/vanta_coder_invoke_incoherence_check.yaml` (Standardized way to trigger a check)
*   **Log**: `logs/agentic_replay.log.jsonl` (Primary data source for detection)
*   **Log Schema**: `.cursor/schemas/agentic_replay_log_entry.schema.json`

## Cross-Agent Workflows (Conceptual)

### 1. Vanta! Coder Pre/Post Major Edit Check

*   **Scenario**: Before or after performing a complex refactoring or potentially risky file modification (e.g., using `mcp_desktop-commander_write_file`).
*   **Workflow**:
    1.  Vanta! Coder identifies the need for a check (based on its internal logic or `.cursor/rules/100-vanta-coder-overlay.mdc`).
    2.  Vanta! Coder (or `VantaMasterCore` on its behalf) invokes the `vanta_coder_invoke_incoherence_check` ritual, potentially targeting specific files involved in the edit.
    3.  Ritual triggers the `IncoherenceDetectionAgent`.
    4.  If incoherence is detected, the `system_incoherence_detected_cascade` is triggered.
    5.  The cascade might notify the user (via `user_notification_agent`) or log warnings.
    6.  Vanta! Coder receives the result (success/failure/reports) and adjusts its next action (e.g., proceed with edit, warn user, request manual intervention).

### 2. Automated Periodic Health Check

*   **Scenario**: Regularly check system coherence as part of routine maintenance.
*   **Workflow**:
    1.  A scheduler (internal to `VantaMasterCore` or external) triggers the `vanta_coder_invoke_incoherence_check` ritual without a `target_file`.
    2.  Detection and cascade triggering proceed as above.
    3.  Results might be logged or sent to a monitoring dashboard.

### 3. Debugging Workflow Integration

*   **Scenario**: User or another agent encounters unexpected errors potentially related to SLI.
*   **Workflow**:
    1.  Debugging agent (or user) invokes the `vanta_coder_invoke_incoherence_check` ritual, potentially targeting files related to the error context.
    2.  The generated `IncoherenceReport` (if any) provides valuable diagnostic information, including relevant log entry IDs and affected files/agents.
    3.  This report can guide further debugging steps or suggest specific resolution paths (manual review, file restore).

## Future Considerations

*   **System Integrity Repair Agent**: A dedicated agent could be developed to attempt automated fixes based on `IncoherenceReport` findings (e.g., reverting conflicting changes, reapplying failed edits). This agent would be a step in the `system_incoherence_detected_cascade`.
*   **Advanced Heuristics**: Implement more sophisticated detection logic in `IncoherenceDetectionAgent` (e.g., analyzing cascade execution order from logs, detecting conflicting parameter usage).
*   **Baseline Checksums**: Integrate a mechanism to store and compare checksums of critical files for faster, more direct incoherence detection.
*   **Visualization**: Develop tools or reports to visualize the findings from the `IncoherenceDetectionAgent`, making it easier to understand complex issues.

This reference provides a starting point for understanding how incoherence detection fits into the broader agentic ecosystem. It should be updated as the detection agent and related workflows evolve. 