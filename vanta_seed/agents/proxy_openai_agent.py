import logging
import asyncio
import os
from typing import Optional, Dict, Any, List
import uuid
import json

# VANTA Imports
from .base_agent import BaseAgent
from vanta_seed.core.data_models import AgentInput, AgentResponse, ToolCall, ToolResponse

# OpenAI Imports (Ensure the 'openai' library is installed)
from openai import AsyncOpenAI # Use Async client
# --- Import OpenAI Error Types --- 
from openai import APIError, RateLimitError, AuthenticationError, OpenAIError
# -------------------------------

# Placeholder for managing threads - simple in-memory dict for now
# In production, this might need persistence or a better caching strategy
openai_threads: Dict[str, str] = {}

class ProxyOpenAIAgent(BaseAgent):
    """A VANTA agent that proxies requests to an OpenAI Assistant."""

    def __init__(self, agent_id: str, config: Optional[dict] = None, orchestrator_ref=None):
        """
        Initializes the proxy agent.
        
        Config expected keys:
            - openai_api_key (optional, defaults to env var)
            - assistant_id: The ID of the OpenAI Assistant to use.
            - poll_interval_ms (optional, defaults to 500)
            - request_timeout_ms (optional, defaults to 120000)
        """
        super().__init__(agent_id, config, orchestrator_ref)
        self.assistant_id = self.config.get("assistant_id")
        self.poll_interval = self.config.get("poll_interval_ms", 500) / 1000.0 # Convert ms to s
        self.request_timeout = self.config.get("request_timeout_ms", 120000) / 1000.0 # Convert ms to s
        
        if not self.assistant_id:
            self.logger.error("Configuration missing required 'assistant_id'. Proxy cannot function.")
            raise ValueError("assistant_id is required in the agent configuration.")
        # --- Basic Safeguard Example: Check assistant_id format ---
        if not isinstance(self.assistant_id, str) or not self.assistant_id.startswith('asst_'):
            self.logger.warning(f"assistant_id '{self.assistant_id}' does not match expected format ('asst_...'). Proceeding, but may cause issues.")
        # ----------------------------------------------------------
            
        # Initialize Async OpenAI Client
        # API key is typically handled by the library via OPENAI_API_KEY env var
        # or can be passed explicitly if needed: api_key=self.config.get("openai_api_key")
        try:
             self.aclient = AsyncOpenAI()
             self.logger.info(f"AsyncOpenAI client initialized for assistant ID: {self.assistant_id}")
        except Exception as e:
             self.logger.error(f"Failed to initialize AsyncOpenAI client: {e}", exc_info=True)
             raise

    async def _get_or_create_thread(self, session_id: str) -> str:
        """Gets the OpenAI thread ID for a session, creating one if needed."""
        thread_id = openai_threads.get(session_id)
        if not thread_id:
            self.logger.info(f"No existing thread found for session '{session_id}'. Creating new thread.")
            try:
                thread = await self.aclient.beta.threads.create()
                thread_id = thread.id
                openai_threads[session_id] = thread_id # Store it
                self.logger.info(f"Created new OpenAI thread {thread_id} for session '{session_id}'.")
            except Exception as e:
                 self.logger.error(f"Failed to create OpenAI thread for session {session_id}: {e}", exc_info=True)
                 raise # Re-raise the exception
        else:
             self.logger.debug(f"Using existing OpenAI thread {thread_id} for session '{session_id}'.")
        return thread_id

    async def execute(self, agent_input: AgentInput) -> AgentResponse:
        """Proxies the input task to the configured OpenAI Assistant."""
        self.logger.info(f"Proxying task to OpenAI Assistant {self.assistant_id}: '{agent_input.task}'")
        session_id = agent_input.session_id or f"proxy_{self.agent_id}_default"
        
        try:
            # 1. Get or Create Thread
            thread_id = await self._get_or_create_thread(session_id)

            # 2. Add Message to Thread
            self.logger.debug(f"Adding message to thread {thread_id}...")
            await self.aclient.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=agent_input.task,
            )
            self.logger.debug("Message added.")

            # 3. Create a Run
            self.logger.debug(f"Creating run for thread {thread_id} with assistant {self.assistant_id}...")
            run = await self.aclient.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id,
                # Instructions could potentially override the assistant's default here if needed
                # instructions="Override instructions for this run..." 
            )
            self.logger.debug(f"Run {run.id} created.")

            # 4. Poll for Run Completion (or tool calls)
            start_time = asyncio.get_event_loop().time()
            while run.status in ['queued', 'in_progress', 'requires_action']:
                # Check for timeout
                if (asyncio.get_event_loop().time() - start_time) > self.request_timeout:
                    self.logger.error(f"OpenAI run {run.id} timed out after {self.request_timeout} seconds.")
                    # Attempt to cancel the run
                    try:
                        await self.aclient.beta.threads.runs.cancel(thread_id=thread_id, run_id=run.id)
                    except Exception as cancel_err:
                        self.logger.warning(f"Failed to cancel timed out run {run.id}: {cancel_err}")
                    return AgentResponse(output="Error: The request timed out.", status='error', error_message="Request timed out")
                
                await asyncio.sleep(self.poll_interval) # Wait before polling again
                run = await self.aclient.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                self.logger.debug(f"Polling run {run.id}: Status = {run.status}")

                # --- Handle requires_action (Tool Calls) --- 
                if run.status == 'requires_action':
                    self.logger.info(f"Run {run.id} requires tool action. Processing...")
                    required_action = run.required_action
                    if not required_action or not required_action.submit_tool_outputs or not required_action.submit_tool_outputs.tool_calls:
                         self.logger.error(f"Run {run.id} requires action, but tool call details are missing.")
                         # Cancel run as we cannot proceed
                         await self.aclient.beta.threads.runs.cancel(thread_id=thread_id, run_id=run.id)
                         return AgentResponse(output="Error: Assistant required action but details were missing.", status='error', error_message="Missing tool call details in required_action")

                    openai_tool_calls = required_action.submit_tool_outputs.tool_calls
                    vanta_tool_responses: List[ToolResponse] = []

                    # Check if orchestrator reference and tool execution method exist
                    if not self.orchestrator or not hasattr(self.orchestrator, '_execute_tool_calls'):
                        self.logger.error("Orchestrator reference or '_execute_tool_calls' method not available. Cannot execute tools.")
                        await self.aclient.beta.threads.runs.cancel(thread_id=thread_id, run_id=run.id)
                        return AgentResponse(output="Error: Internal configuration error prevents tool execution.", status='error', error_message="Orchestrator tool execution unavailable")

                    # 1. Translate OpenAI tool calls to VANTA ToolCall format
                    vanta_tool_calls_to_run: List[ToolCall] = []
                    openai_call_id_map: Dict[str, str] = {} # Map VANTA call ID -> OpenAI call ID
                    
                    for oai_call in openai_tool_calls:
                         if oai_call.type == 'function':
                              # Generate a unique ID for the VANTA call
                              vanta_call_id = f"vtool_{uuid.uuid4().hex[:8]}"
                              openai_call_id_map[vanta_call_id] = oai_call.id # Store mapping
                              
                              vanta_tool_call = ToolCall(
                                   id=vanta_call_id, # Use VANTA's ID format
                                   function={
                                        "name": oai_call.function.name,
                                        "arguments": oai_call.function.arguments # Arguments are already strings (usually JSON)
                                   }
                                   # type defaults to function
                              )
                              vanta_tool_calls_to_run.append(vanta_tool_call)
                              self.logger.debug(f"Translated OpenAI tool call {oai_call.id} (Func: {oai_call.function.name}) to VANTA call {vanta_call_id}")
                         else:
                              self.logger.warning(f"Unsupported OpenAI tool type '{oai_call.type}' requested. Skipping call ID: {oai_call.id}")
                              # Optionally submit an error response for this specific call later

                    # 2. Execute tools using VANTA orchestrator
                    if vanta_tool_calls_to_run:
                        self.logger.info(f"Executing {len(vanta_tool_calls_to_run)} tool(s) via VANTA orchestrator...")
                        # We pass self.agent_id as the requesting agent ID to _execute_tool_calls
                        vanta_tool_responses = await self.orchestrator._execute_tool_calls(self.agent_id, vanta_tool_calls_to_run)
                        self.logger.info("VANTA tool execution completed.")
                    else:
                         self.logger.warning("No translatable tool calls found in requires_action.")
                         # If no tools could be run, we might need to cancel or handle differently
                         # For now, proceed to submit empty/error responses if necessary
                         pass 

                    # 3. Translate VANTA ToolResponse back to OpenAI format and Prepare outputs for submission
                    tool_outputs_for_openai = []
                    for vanta_resp in vanta_tool_responses:
                        openai_tool_call_id = openai_call_id_map.get(vanta_resp.tool_call_id)
                        if not openai_tool_call_id:
                             self.logger.warning(f"Could not find matching OpenAI call ID for VANTA response ID {vanta_resp.tool_call_id}. Skipping submission for this response.")
                             continue
                             
                        # OpenAI expects the output content for the tool
                        # We should pass the content directly. If there was an error, the content field in vanta_resp should contain the error message.
                        tool_outputs_for_openai.append({
                            "tool_call_id": openai_tool_call_id,
                            "output": vanta_resp.content 
                        })
                        self.logger.debug(f"Prepared output for OpenAI tool call {openai_tool_call_id} (VANTA ID: {vanta_resp.tool_call_id}), Status: {vanta_resp.status}")

                    # 4. Submit tool outputs back to OpenAI Run
                    if tool_outputs_for_openai:
                        self.logger.info(f"Submitting {len(tool_outputs_for_openai)} tool output(s) back to OpenAI run {run.id}...")
                        try:
                            run = await self.aclient.beta.threads.runs.submit_tool_outputs(
                                thread_id=thread_id,
                                run_id=run.id,
                                tool_outputs=tool_outputs_for_openai,
                            )
                            self.logger.info("Tool outputs submitted successfully.")
                            # Loop will continue polling with the updated run status
                            continue # Skip rest of the loop and poll again
                        except Exception as submit_err:
                            self.logger.error(f"Failed to submit tool outputs for run {run.id}: {submit_err}", exc_info=True)
                            # Decide how to handle submission failure - maybe cancel run?
                            await self.aclient.beta.threads.runs.cancel(thread_id=thread_id, run_id=run.id)
                            return AgentResponse(output="Error: Failed to submit tool results back to assistant.", status='error', error_message=f"Failed to submit tool outputs: {submit_err}")
                    else:
                         # This case might occur if all requested tools were unsupported types
                         self.logger.warning(f"No tool outputs to submit for run {run.id}. Cancelling run.")
                         await self.aclient.beta.threads.runs.cancel(thread_id=thread_id, run_id=run.id)
                         return AgentResponse(output="Error: Assistant requested unsupported tools.", status='error', error_message="No valid tool outputs could be generated or submitted")
                # --------------------------------------------------

            # 5. Process Final Status
            if run.status == 'completed':
                self.logger.debug(f"Run {run.id} completed. Fetching messages...")
                messages = await self.aclient.beta.threads.messages.list(thread_id=thread_id, order="desc", limit=1)
                # Get the latest assistant message
                if messages.data and messages.data[0].role == "assistant":
                     assistant_response = "".join([content.text.value for content in messages.data[0].content if hasattr(content, 'text')])
                     self.logger.info(f"Received response from OpenAI Assistant {self.assistant_id}")
                     # Generate a simple memory event
                     memory_event = self._generate_memory_event(
                          decision="proxied_openai_response",
                          reason=f"Received response from Assistant {self.assistant_id}",
                          payload={"input_task": agent_input.task, "assistant_output": assistant_response}
                     )
                     # Trigger circulation 
                     if self.orchestrator:
                          self.orchestrator._trigger_circulation(self.agent_id, memory_event)
                          
                     return AgentResponse(output=assistant_response, status='success', memory_event=memory_event)
                else:
                     self.logger.error(f"Run {run.id} completed, but no recent assistant message found.")
                     return AgentResponse(output="Error: Assistant did not provide a response.", status='error', error_message="No assistant message found after completion")
            else:
                # Handle other terminal statuses (failed, cancelled, expired)
                error_message = f"OpenAI run {run.id} finished with status: {run.status}. Error: {run.last_error}"
                self.logger.error(error_message)
                return AgentResponse(output=f"Error: Assistant run failed ({run.status}).", status='error', error_message=error_message)

        # --- Enhanced Error Handling --- 
        except AuthenticationError as e:
             self.logger.error(f"OpenAI Authentication Error: {e}", exc_info=True)
             return AgentResponse(output="Error: OpenAI authentication failed. Check API key.", status='error', error_message=f"AuthError: {e}")
        except RateLimitError as e:
             self.logger.error(f"OpenAI Rate Limit Error: {e}", exc_info=True)
             # Potential TODO: Implement backoff/retry?
             return AgentResponse(output="Error: OpenAI rate limit exceeded. Please try again later.", status='error', error_message=f"RateLimitError: {e}")
        except APIError as e: # Catch other specific OpenAI API errors
             self.logger.error(f"OpenAI API Error: {e}", exc_info=True)
             return AgentResponse(output=f"Error: An issue occurred with the OpenAI API ({e.status_code}).", status='error', error_message=f"APIError: {e}")
        except OpenAIError as e: # Catch broader OpenAI errors
             self.logger.error(f"General OpenAI Error: {e}", exc_info=True)
             return AgentResponse(output=f"Error: An OpenAI library error occurred.", status='error', error_message=f"OpenAIError: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected Error during OpenAI Assistant execution: {e}", exc_info=True)
            return AgentResponse(output=f"Error interacting with OpenAI: {e}", status='error', error_message=str(e))
        # -----------------------------

    async def receive_message(self, message: AgentMessage):
        """Proxy agents typically don't handle direct A2A messages, but subclasses could override."""
        self.logger.warning(f"Received A2A message {message.message_id}, but ProxyOpenAIAgent does not implement custom handling.")
        # Default behavior is to do nothing.
        pass 