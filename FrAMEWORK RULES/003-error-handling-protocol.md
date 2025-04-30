# VANTA Framework Rule: Error Handling Protocol

## Principle: Resilience, Clarity, and Recovery

Error handling within the VANTA framework should aim for resilience against failures, provide clear context about errors, and facilitate graceful recovery or reporting, minimizing disruption to the overall system.

## Rationale

In a distributed agent system, errors are inevitable. A standardized approach to handling them ensures that failures in one component are managed predictably, preventing cascading failures and aiding diagnosis.

## Protocol Steps

1.  **Identify Potential Failure Points:**
    *   Actively consider potential failure modes during design and implementation (e.g., network issues, API failures, invalid data, resource exhaustion, internal logic errors).

2.  **Use Specific Exceptions:**
    *   Define custom exception classes within VANTA (e.g., in `vanta_seed.core.exceptions`) for common framework-specific errors (e.g., `AgentCommunicationError`, `ConfigurationError`, `TaskProcessingError`, `MemoryError`).
    *   Catch specific exceptions rather than broad `Exception` where possible to handle different errors appropriately.
    *   Avoid catching `BaseException` unless absolutely necessary (e.g., top-level cleanup).

3.  **Contextual Error Messages:**
    *   Ensure error messages are informative, including:
        *   What operation was being attempted.
        *   Key parameters or identifiers involved (e.g., agent ID, task ID, target URL).
        *   The nature of the error.
    *   Avoid exposing sensitive details in error messages that might reach end-users or external systems.

4.  **Log Errors Before Handling/Raising:**
    *   Always log errors with sufficient context (including stack traces via `exc_info=True`) before handling, suppressing, or re-raising them.
    *   Refer to `FrAMEWORK RULES/002-logging-standards.md`.

5.  **Handling Strategies (Choose Appropriately):**
    *   **Retry:** For transient errors (e.g., network timeouts), implement a retry mechanism with exponential backoff.
    *   **Fallback:** If a primary operation fails, attempt a fallback or provide a default value/behavior if appropriate.
    *   **Graceful Degradation:** Allow the system to continue operating with reduced functionality if a non-critical component fails.
    *   **Report and Continue:** Log the error and potentially notify monitoring, but allow the current process to continue if the error is recoverable or non-fatal.
    *   **Report and Fail:** For critical errors, log the error, potentially notify, and then fail the current operation cleanly (e.g., return an error response, raise a specific exception).

6.  **Error Propagation:**
    *   When catching an exception and raising a new one, chain the original exception (`raise NewException("Context") from original_exception`) to preserve the root cause.
    *   Define clear error reporting mechanisms between agents and the orchestrator (e.g., standardized error fields in task results).

7.  **Resource Cleanup:**
    *   Use `try...finally` blocks or context managers (`with` statement) to ensure resources (files, network connections, locks) are released even if errors occur.

8.  **Agent/Orchestrator Level Handling:**
    *   The `AgentOrchestrator` should have robust top-level error handling to catch unhandled exceptions from agents, log them, and potentially decide whether to restart an agent or mark a task as failed.
    *   Individual agents are responsible for handling errors within their specific task logic according to these guidelines.

## Related Guidelines

*   `FrAMEWORK RULES/002-logging-standards.md`: Defines how errors should be logged.
*   `.cursor/rules/300-error-handling.mdc`: Provides general error handling guidelines relevant to AI assistance during coding.

## Adherence

All components within the VANTA framework must implement error handling consistent with this protocol. 