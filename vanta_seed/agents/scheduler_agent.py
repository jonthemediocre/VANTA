import asyncio
import logging
from typing import Dict, Any, Optional
from vanta_seed.agents.base_agent import BaseAgent # Assuming BaseAgent exists
# from vanta_seed.core.vanta_master_core import VantaMasterCore # Avoid circular import, use self.orchestrator

logger = logging.getLogger(__name__)

class SchedulerAgent(BaseAgent):
    """
    An agent responsible for scheduling and executing periodic tasks (rituals)
    within the VANTA framework.
    """
    def __init__(self, agent_name: str, definition: Dict[str, Any], blueprint: Dict[str, Any], all_agent_definitions: Dict[str, Any], orchestrator):
        super().__init__(agent_name, definition, blueprint, all_agent_definitions, orchestrator)
        agent_config = definition.get("config", {})
        self.schedule_config = agent_config.get("schedule", [])
        self.interval_seconds = agent_config.get("check_interval_seconds", 60)
        self.misfire_grace_seconds = agent_config.get("misfire_grace_seconds", 3600)
        self.max_retries = agent_config.get("max_retries", 3) # Default 3 retries
        self.base_retry_delay_seconds = agent_config.get("base_retry_delay_seconds", 10) # Default 10s base delay
        self._schedule_loop_task: Optional[asyncio.Task] = None
        self._running = False
        logger.info(f"SchedulerAgent '{agent_name}' initialized with {len(self.schedule_config)} tasks. Interval: {self.interval_seconds}s, Misfire Grace: {self.misfire_grace_seconds}s, Max Retries: {self.max_retries}")

    async def startup(self):
        """Starts the scheduler loop when the agent starts."""
        logger.info(f"SchedulerAgent '{self.agent_name}' starting up.")
        self._running = True
        if not self._schedule_loop_task or self._schedule_loop_task.done():
            self._job_states = { 
                task_config.get("name"): {"last_run": 0, "next_run": 0, "retry_count": 0}
                for task_config in self.schedule_config if task_config.get("name")
            }
            self._schedule_loop_task = asyncio.create_task(self._run_schedule_loop())
            logger.info(f"SchedulerAgent '{self.agent_name}' schedule loop started.")
        else:
            logger.warning(f"SchedulerAgent '{self.agent_name}' schedule loop already running.")

    async def shutdown(self):
        """Stops the scheduler loop gracefully."""
        logger.info(f"SchedulerAgent '{self.agent_name}' shutting down.")
        self._running = False
        if self._schedule_loop_task and not self._schedule_loop_task.done():
            self._schedule_loop_task.cancel()
            try:
                await self._schedule_loop_task
            except asyncio.CancelledError:
                logger.info(f"SchedulerAgent '{self.agent_name}' schedule loop successfully cancelled.")
            except Exception as e:
                logger.error(f"Error during scheduler loop cancellation: {e}", exc_info=True)
        self._schedule_loop_task = None
        logger.info(f"SchedulerAgent '{self.agent_name}' shutdown complete.")

    async def _run_schedule_loop(self):
        """The main loop that checks the schedule and triggers tasks."""
        logger.info("Scheduler loop running...")
        initial_time = asyncio.get_event_loop().time()
        for task_config in self.schedule_config:
            task_name = task_config.get("name")
            if task_name and task_name in self._job_states and task_config.get("run_on_startup", False):
                self._job_states[task_name]["next_run"] = initial_time

        while self._running:
            try:
                current_time = asyncio.get_event_loop().time()
                for task_config in self.schedule_config:
                    task_name = task_config.get("name")
                    if not task_name:
                        logger.warning("Scheduled task found without a 'name'. Skipping.")
                        continue
                    
                    interval = task_config.get("interval_seconds", 3600) 
                    last_run = self._job_states[task_name]["last_run"]
                    task_payload = task_config.get("payload", {}) 
                    run_immediately = task_config.get("run_on_startup", False)

                    # Determine if the task is due based on interval
                    is_due = False
                    if last_run == 0 and run_immediately:
                        is_due = True 
                    elif interval > 0 and (current_time - last_run) >= interval: # Check interval > 0
                        is_due = True
                    # Note: If interval <= 0, it will never run based on time

                    if is_due:
                        # <<< START Misfire Check >>>
                        scheduled_run_time = last_run + interval
                        # We only check misfire if it wasn't run_immediately (last_run != 0)
                        if last_run != 0 and self.misfire_grace_seconds >= 0: # Allow disabling misfire check with -1
                            overdue_seconds = current_time - scheduled_run_time
                            if overdue_seconds > self.misfire_grace_seconds:
                                logger.warning(f"Scheduler: MISSED task '{task_name}' due at {scheduled_run_time:.0f} by {overdue_seconds:.0f}s (grace {self.misfire_grace_seconds}s). Skipping run.")
                                self._job_states[task_name]["last_run"] = current_time # Reset last run to now
                                self._job_states[task_name]["retry_count"] += 1
                                if self._job_states[task_name]["retry_count"] <= self.max_retries:
                                    self._job_states[task_name]["next_run"] = current_time + self.base_retry_delay_seconds
                                else:
                                    logger.error(f"Scheduler: MAX RETRIES reached for task '{task_name}'. Skipping further retries.")
                                continue # Skip the rest of the loop for this task
                        # <<< END Misfire Check >>>
                        
                        # If not misfired (or first run), proceed to submit
                        logger.info(f"Scheduler: Triggering scheduled task '{task_name}'...")
                        task_to_submit = {
                            "intent": task_config.get("intent"), 
                            "payload": task_payload,
                            "context": {"source": "scheduler", "scheduled_task_name": task_name}
                        }
                        if task_config.get("target_agent"): 
                            task_to_submit["target_agent"] = task_config.get("target_agent")
                            
                        try:
                            asyncio.create_task(self.orchestrator.submit_task(task_to_submit))
                            self._job_states[task_name]["last_run"] = current_time # Update last run time *after* successful submission trigger
                            logger.info(f"Scheduler: Task '{task_name}' submitted to orchestrator.")
                        except Exception as e:
                            logger.error(f"Scheduler: Error submitting task '{task_name}' to orchestrator: {e}", exc_info=True)
                            # Do NOT update last_run_time here if submission failed, let it retry next cycle
                            
                # Wait until the next check interval
                await asyncio.sleep(self.interval_seconds)

            except asyncio.CancelledError:
                logger.info("Scheduler loop cancellation requested.")
                break 
            except Exception as e:
                logger.error(f"Scheduler: Unexpected error in schedule loop: {e}", exc_info=True)
                await asyncio.sleep(self.interval_seconds * 2) 

        logger.info("Scheduler loop finished.")

    async def handle_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handles direct tasks if needed, e.g., to dynamically update schedule."""
        intent = task_data.get("intent")
        logger.info(f"SchedulerAgent received task with intent: {intent}")
        
        if intent == "update_schedule":
            new_schedule = task_data.get("payload", {}).get("schedule")
            if isinstance(new_schedule, list):
                logger.warning("Dynamic schedule updates while running are experimental.")
                self.schedule_config = new_schedule
                self._job_states = { 
                    task_config.get("name"): {"last_run": 0, "next_run": 0, "retry_count": 0}
                    for task_config in self.schedule_config if task_config.get("name")
                }
                logger.info("SchedulerAgent schedule updated. Job states reset.")
                return {"status": "success", "message": "Schedule updated."}
            else:
                logger.warning("Invalid payload for update_schedule intent.")
                return {"status": "error", "message": "Invalid schedule payload."}
        
        elif intent == "get_schedule":
             return {"status": "success", "schedule": self.schedule_config, "job_states": self._job_states}
             
        elif intent == "trigger_task":
             task_name_to_trigger = task_data.get("payload", {}).get("task_name")
             if task_name_to_trigger and task_name_to_trigger in self._job_states:
                  logger.info(f"Attempting to manually trigger task: {task_name_to_trigger}")
                  self._job_states[task_name_to_trigger]["next_run"] = asyncio.get_event_loop().time()
                  self._job_states[task_name_to_trigger]["retry_count"] = 0 
                  return {"status": "success", "message": f"Task '{task_name_to_trigger}' scheduled for immediate run."}
             elif task_name_to_trigger:
                 logger.warning(f"Task '{task_name_to_trigger}' not found in current schedule state.")
                 return {"status": "error", "message": "Task not found in schedule state."}
             else:
                  logger.warning("No task_name provided for trigger_task intent.")
                  return {"status": "error", "message": "Missing task_name in payload."}

        return {"status": "ignored", "message": f"Intent '{intent}' not handled by SchedulerAgent."}

# Example BaseAgent structure (replace with actual import)
# class BaseAgent:
#     def __init__(self, agent_name, definition, blueprint, all_agent_definitions, orchestrator):
#         self.agent_name = agent_name
#         self.definition = definition
#         self.blueprint = blueprint
#         self.all_agent_definitions = all_agent_definitions
#         self.orchestrator = orchestrator # Reference to VantaMasterCore
#     async def startup(self): pass
#     async def shutdown(self): pass
#     async def handle_task(self, task_data): return {"status": "not_implemented"} 