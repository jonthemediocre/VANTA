# VANTA Framework Rule: Logging Standards

## Principle: Clarity, Context, and Consistency

Logging within the VANTA framework should provide clear, contextual, and consistent information to aid debugging, monitoring, and understanding system behavior.

## Rationale

Effective logging is crucial for diagnosing issues in a complex, potentially asynchronous multi-agent system. Standardized logging ensures that logs are informative and easily parseable, whether by humans or automated tools.

## Standards

1.  **Logger Instantiation:**
    *   Use the utility function `vanta_seed.utils.logging_utils.get_vanta_logger(name)` where possible.
    *   Logger names should follow a hierarchical pattern, typically `Module.Class` or `Agent.AgentName` (e.g., `Orchestrator.Core`, `Agent.MemoryWeaver`).

2.  **Log Message Format:**
    *   Adhere to the format defined in `config.py` or the logging setup (default: `%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(name)s - %(message)s`).
    *   Ensure messages are concise yet informative.

3.  **Contextual Information:**
    *   **Agent/Module ID:** Automatically included via the logger name.
    *   **Task ID:** When logging within the context of processing a specific task, include the `task_id` if available.
        *   *Example:* `logger.info(f"Task {task_id}: Processing intent '{intent}'.")`
    *   **Correlation ID:** For operations spanning multiple agents or steps, include a `correlation_id` if available.
    *   **Relevant State:** Include key state variables pertinent to the log message where appropriate, but avoid logging overly large objects or sensitive data.
        *   *Example:* `logger.debug(f"Agent {self.name}: Position updated to {new_position}")`

4.  **Log Levels:**
    *   **DEBUG:** Detailed information, typically of interest only when diagnosing problems (e.g., variable values, fine-grained step execution, state changes).
    *   **INFO:** Confirmation that things are working as expected (e.g., service startup, task reception, successful completion of significant operations).
    *   **WARNING:** An indication that something unexpected happened, or indicative of a potential problem, but the software is still working (e.g., configuration fallback, recoverable error, unexpected state).
    *   **ERROR:** Due to a more serious problem, the software has not been able to perform some function (e.g., failed task processing, exception during core logic, connection failure).
    *   **CRITICAL:** A serious error, indicating that the program itself may be unable to continue running (e.g., failure to load essential config, unrecoverable system error).

5.  **Error Logging:**
    *   When logging exceptions, use `logger.error(..., exc_info=True)` to include the stack trace automatically.
    *   Log errors *before* raising exceptions or returning error responses, providing context about the operation that failed.

6.  **Performance Considerations:**
    *   Avoid excessive logging (especially DEBUG) in performance-critical loops.
    *   Do not construct complex log messages if the log level is disabled (use level checks like `if logger.isEnabledFor(logging.DEBUG): ...`).

7.  **Security:**
    *   **Never log sensitive information** such as API keys, passwords, personal data, or raw sensitive payloads.
    *   Sanitize data before logging if necessary.

8.  **Configuration:**
    *   Log level should be configurable (e.g., via environment variables or `config.py`).
    *   Log output destination (console, file) should be configurable.

## Adherence

All new and modified code within the VANTA framework should adhere to these logging standards. 