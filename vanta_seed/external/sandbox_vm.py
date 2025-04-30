# vanta_seed/external/sandbox_vm.py
import logging
import subprocess
import os

class SandboxVM:
    """Placeholder for executing code within a secure sandbox (e.g., Docker, Firecracker)."""
    def __init__(self, config=None, **kwargs):
        self.config = config or {}
        self.logger = logging.getLogger(f"External.SandboxVM")
        self.logger.info("SandboxVM Initialized (Placeholder - No actual sandbox).")
        # TODO: Initialize connection to Docker/Firecracker/etc.

    def execute_code(self, code: str, language: str = 'python') -> dict:
        """Executes the provided code string in the configured sandbox."""
        self.logger.info(f"Attempting to execute {language} code in sandbox (Placeholder)...")
        self.logger.debug(f"Code: {code[:200]}...")
        
        if language != 'python':
             self.logger.warning(f"Sandbox execution only supports python currently (requested: {language}).")
             return {"success": False, "error": f"Unsupported language: {language}", "output": None}

        # --- Basic Placeholder: Execute Python using subprocess --- 
        # WARNING: This is NOT a secure sandbox. It runs code directly on the host.
        # Replace this with actual Docker/Firecracker execution logic.
        try:
            # Use subprocess.run for simplicity, capture output and errors
            timeout_seconds = self.config.get('sandbox_timeout', 10) # Default timeout
            result = subprocess.run(
                ["python", "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False # Don't raise exception on non-zero exit code
            )
            
            output = result.stdout
            error_output = result.stderr
            exit_code = result.returncode
            
            self.logger.info(f"Subprocess execution finished with exit code: {exit_code}")
            
            if exit_code == 0:
                return {"success": True, "output": output, "error": error_output or None}
            else:
                # Include stderr in the error message if execution failed
                error_message = f"Code execution failed with exit code {exit_code}."
                if error_output:
                     error_message += f"\nStderr:\n{error_output}"
                return {"success": False, "error": error_message, "output": output}

        except subprocess.TimeoutExpired:
            self.logger.error(f"Code execution timed out after {timeout_seconds} seconds.")
            return {"success": False, "error": "Execution timed out", "output": None}
        except Exception as e:
            self.logger.error(f"Error executing code via subprocess: {e}", exc_info=True)
            return {"success": False, "error": f"Subprocess execution failed: {e}", "output": None}
        # --- End Placeholder --- 

    async def handle(self, task_data):
        """Handles tasks specifically routed to the SandboxVM."""
        self.logger.debug(f"Handling task: {task_data.get('intent')}")
        intent = task_data.get('intent')
        payload = task_data.get('payload', {})
        
        if intent == 'execute_code_in_sandbox':
            code_to_run = payload.get('code')
            language = payload.get('language', 'python')
            if not code_to_run:
                 return {"success": False, "error": "No code provided in payload."}
                 
            # This execution is blocking, consider running in executor for async context
            result = self.execute_code(code_to_run, language)
            return result # Return the dict from execute_code
        else:
             self.logger.warning(f"Received unhandled intent: {intent}")
             return {"success": False, "error": "Unhandled intent for SandboxVM"}

# Example Usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sandbox = SandboxVM()
    
    print("\n--- Testing Code Execution (Placeholder - UNSAFE) --- ")
    
    py_code_success = "import os\nprint('Current directory:', os.getcwd())"
    result1 = sandbox.execute_code(py_code_success)
    print(f"Result 1 (Success Case):\nSuccess: {result1.get('success')}\nOutput:\n{result1.get('output')}\nError: {result1.get('error')}")
    
    print("-" * 20)
    
    py_code_error = "print('Hello')\nimport non_existent_module\nprint('World')"
    result2 = sandbox.execute_code(py_code_error)
    print(f"Result 2 (Error Case):\nSuccess: {result2.get('success')}\nOutput:\n{result2.get('output')}\nError:\n{result2.get('error')}")

    print("-" * 20)

    unsupported_lang_code = "console.log('hello from js');"
    result3 = sandbox.execute_code(unsupported_lang_code, language='javascript')
    print(f"Result 3 (Unsupported Lang):\nSuccess: {result3.get('success')}\nOutput:\n{result3.get('output')}\nError:\n{result3.get('error')}") 