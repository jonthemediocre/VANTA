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
        self.schedule_config = definition.get("config", {}).get("schedule", [])
        self.interval_seconds = definition.get("config", {}).get("check_interval_seconds", 60) # Default check every 60s
        self._schedule_loop_task: Optional[asyncio.Task] = None
        self._running = False
        logger.info(f"SchedulerAgent '{agent_name}' initialized with {len(self.schedule_config)} scheduled tasks.")

    async def startup(self):
        """Starts the scheduler loop when the agent starts."""
        logger.info(f"SchedulerAgent '{self.agent_name}' starting up.")
        self._running = True
        if not self._schedule_loop_task or self._schedule_loop_task.done():
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
        # Use a dictionary to store last run times, initializing to 0
        last_run_times = {task_config.get("name"): 0 for task_config in self.schedule_config if task_config.get("name")}

        while self._running:
            try:
                current_time = asyncio.get_event_loop().time()
                for task_config in self.schedule_config:
                    task_name = task_config.get("name")
                    if not task_name:
                        logger.warning("Scheduled task found without a 'name'. Skipping.")
                        continue
                    
                    interval = task_config.get("interval_seconds", 3600) # Default 1 hour
                    last_run = last_run_times.get(task_name, 0)
                    task_payload = task_config.get("payload", {}) # Optional payload
                    run_immediately = task_config.get("run_on_startup", False) # Option to run immediately

                    if last_run == 0 and run_immediately:
                         # Run immediately on first check if configured
                         needs_run = True
                    elif (current_time - last_run) >= interval:
                         needs_run = True
                    else:
                         needs_run = False

                    if needs_run:
                        logger.info(f"Scheduler: Triggering scheduled task '{task_name}'...")
                        # Always use the public submit_task method now
                        task_to_submit = {
                            "intent": task_config.get("intent"), # Assuming intent is defined in schedule
                            "payload": task_payload,
                            "context": {"source": "scheduler", "scheduled_task_name": task_name}
                        }
                        if task_config.get("target_agent"): # Allow optional target agent override
                            task_to_submit["target_agent"] = task_config.get("target_agent")
                            
                        try:
                            # Use asyncio.create_task to avoid blocking the scheduler loop
                            asyncio.create_task(self.orchestrator.submit_task(task_to_submit))
                            last_run_times[task_name] = current_time
                            logger.info(f"Scheduler: Task '{task_name}' submitted to orchestrator.")
                        except Exception as e:
                            logger.error(f"Scheduler: Error submitting task '{task_name}' to orchestrator: {e}", exc_info=True)
                            
                        # Update last run time even if submission fails to avoid rapid retries
                        last_run_times[task_name] = current_time

                # Wait until the next check interval
                await asyncio.sleep(self.interval_seconds)

            except asyncio.CancelledError:
                logger.info("Scheduler loop cancellation requested.")
                break # Exit the loop cleanly
            except Exception as e:
                logger.error(f"Scheduler: Unexpected error in schedule loop: {e}", exc_info=True)
                # Avoid rapid looping on persistent errors
                await asyncio.sleep(self.interval_seconds * 2)

        logger.info("Scheduler loop finished.")

    async def handle_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handles direct tasks if needed, e.g., to dynamically update schedule."""
        intent = task_data.get("intent")
        logger.info(f"SchedulerAgent received task with intent: {intent}")
        
        if intent == "update_schedule":
            new_schedule = task_data.get("payload", {}).get("schedule")
            if isinstance(new_schedule, list):
                self.schedule_config = new_schedule
                # Reset last run times for potentially new/removed tasks
                # Be careful with direct access if loop is running - consider using a lock or queue
                last_run_times = {task_config.get("name"): 0 for task_config in self.schedule_config if task_config.get("name")}
                logger.info("SchedulerAgent schedule updated.")
                return {"status": "success", "message": "Schedule updated."}
            else:
                logger.warning("Invalid payload for update_schedule intent.")
                return {"status": "error", "message": "Invalid schedule payload."}
        
        elif intent == "get_schedule":
             return {"status": "success", "schedule": self.schedule_config}
             
        elif intent == "trigger_task":
             task_name_to_trigger = task_data.get("payload", {}).get("task_name")
             if task_name_to_trigger:
                  logger.info(f"Attempting to manually trigger task: {task_name_to_trigger}")
                  # Find task config
                  task_config = next((t for t in self.schedule_config if t.get("name") == task_name_to_trigger), None)
                  if task_config:
                       target_orchestrator_method = task_config.get("orchestrator_method")
                       task_payload = task_config.get("payload", {})
                       if target_orchestrator_method and hasattr(self.orchestrator, target_orchestrator_method):
                            try:
                                method_to_call = getattr(self.orchestrator, target_orchestrator_method)
                                if task_payload:
                                    asyncio.create_task(method_to_call(task_payload))
                                else:
                                    asyncio.create_task(method_to_call())
                                return {"status": "success", "message": f"Task '{task_name_to_trigger}' triggered."}
                            except Exception as e:
                                logger.error(f"Error triggering task '{task_name_to_trigger}': {e}", exc_info=True)
                                return {"status": "error", "message": f"Error triggering task: {e}"}
                       else:
                            logger.warning(f"Orchestrator method '{target_orchestrator_method}' not found for task '{task_name_to_trigger}'.")
                            return {"status": "error", "message": "Target method not found."}
                  else:
                       logger.warning(f"Task '{task_name_to_trigger}' not found in schedule.")
                       return {"status": "error", "message": "Task not found in schedule."}
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