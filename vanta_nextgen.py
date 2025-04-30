import re
import json
import os
import datetime
from shutil import copy2
import filelock
import uuid
import subprocess
from dataclasses import dataclass
import requests
import random
import importlib
from pathlib import Path
from jsonschema import validate, ValidationError
import logging

# --- Add a module-level logger FOR THIS FILE if needed by other classes --- 
logger = logging.getLogger(__name__)
# -------------------------------------------------------------------------

class AgendaScout:
    def __init__(self, roadmap_path="roadmap.json", season_value="money"):
        self.roadmap_path = roadmap_path
        self.season_value = season_value
        if not os.path.exists(self.roadmap_path):
            print(f"Warning: Roadmap file not found at {self.roadmap_path}")

    def choose(self):
        """Loads roadmap and chooses the first milestone with status 'todo'."""
        try:
            if not os.path.exists(self.roadmap_path):
                print(f"Error: Roadmap file not found at {self.roadmap_path}")
                return None
                
            with open(self.roadmap_path, 'r') as f:
                roadmap_data = json.load(f)
            
            if not isinstance(roadmap_data, list):
                 print(f"Error: Expected roadmap root to be a list of goals.")
                 return None
                 
            for goal in roadmap_data:
                if 'milestones' in goal and isinstance(goal['milestones'], list):
                    for milestone in goal['milestones']:
                        if isinstance(milestone, dict) and milestone.get('status') == 'todo':
                            milestone['goal'] = goal.get('goal', 'Unknown Goal') 
                            return milestone
            
            return None
            
        except json.JSONDecodeError:
            print(f"Error: Failed to decode JSON from {self.roadmap_path}")
            return None
        except Exception as e:
            print(f"Error loading or processing roadmap: {e}")
            return None

class MoERouter:
    # TODO: Integrate with a more robust prompt classification mechanism
    # TODO: Load routing strategy dynamically (e.g., from blueprint.yaml via orchestrator)
    def __init__(self, routing_strategy=None):
        # Default routing strategy if none provided (Matches blueprint.yaml)
        self.strategy = routing_strategy or {
            'default': 'deepseek',
            'vision': 'llama4',
            'code_math': 'nemotron',
            'fallback': 'deepseek'
        }
        # Basic keyword patterns for classification
        self.vision_keywords = re.compile(r'\b(image|visual|picture|see|look at|show me)\b', re.IGNORECASE)
        self.code_math_keywords = re.compile(r'\b(code|python|javascript|java|c\+\+|calculate|math|equation|solve for|algorithm)\b', re.IGNORECASE)

    def select_llm(self, prompt: str, task_type: str | None = None) -> str:
        """Selects the appropriate LLM based on prompt content or task type."""
        if task_type == 'vision' or self.vision_keywords.search(prompt):
            return self.strategy.get('vision', self.strategy['fallback'])
        
        if task_type == 'code_math' or self.code_math_keywords.search(prompt):
            return self.strategy.get('code_math', self.strategy['fallback'])

        return self.strategy.get('default', self.strategy['fallback'])

    # Kept for potential compatibility, but select_llm is preferred
    def choose(self, prompt: str) -> str:
        return self.select_llm(prompt)

class SandboxVM:
    """Executes shell commands in a sandboxed environment with timeout and error handling."""
    def __init__(self, timeout_s=3, retries=1):
        self.timeout_s = timeout_s
        self.retries = retries

    def run(self, cmd):
        """Run a command list with timeout, return structured result."""
        attempt = 0
        while attempt <= self.retries:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_s,
                    check=True
                )
                return {
                    'success': True,
                    'stdout': result.stdout.strip(),
                    'stderr': result.stderr.strip(),
                    'returncode': result.returncode
                }
            except subprocess.TimeoutExpired as e:
                return {
                    'success': False,
                    'error': 'timeout',
                    'stdout': e.stdout or '',
                    'stderr': e.stderr or ''
                }
            except subprocess.CalledProcessError as e:
                return {
                    'success': False,
                    'error': 'execution_error',
                    'stdout': e.stdout or '',
                    'stderr': e.stderr or '',
                    'returncode': e.returncode
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e)
                }
            finally:
                attempt += 1
        return {
            'success': False,
            'error': 'max_retries_exceeded'
        }

class CrossModalMemory:
    """
    Manages multimodal memory storage: text/metadata appended to a JSONL file,
    and media (images, audio) stored in subdirectories.
    Provides concurrency-safe writes with file locking, entry IDs, and metadata.
    """
    def __init__(self, base_path, logger_instance=None):
        # 'base_path' here represents the specific path passed by the agent,
        # e.g., 'memory_store/audio' or 'memory_store/images'
        # The actual memory root will be the parent of this path.
        self.base_path = Path(base_path).resolve()
        self.memory_root = self.base_path.parent
        self.metadata_file = self.memory_root / 'memory_metadata.jsonl'
        self.lock = filelock.FileLock(str(self.metadata_file) + '.lock')
        
        # --- Store and use passed logger --- 
        self.logger = logger_instance or logging.getLogger(__name__) # Use passed or default
        # -----------------------------------
        
        # --- Explicitly create parent directory first ---
        self.memory_root.mkdir(parents=True, exist_ok=True)
        # -----------------------------------------------

        # Ensure base path for the specific data type exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"CrossModalMemory initialized for path: {self.base_path}, Metadata: {self.metadata_file}") # Use self.logger
        # Future: support sqlite or vector DB backends

    def add_text(self, txt: str, agent: str = None, tags: list = None) -> str | None:
        """Add a text entry with unique ID, timestamp, agent, and tags."""
        entry_id = str(uuid.uuid4())
        entry = {
            'id': entry_id,
            'type': 'text',
            'data': txt,
            'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
            'agent': agent,
            'tags': tags or []
        }
        try:
            with self.lock:
                with open(self.metadata_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(entry) + "\n")
            self.logger.debug(f"Added text entry {entry_id}") # Use self.logger
            return entry_id
        except Exception as e:
            self.logger.error(f"Error writing text memory metadata: {e}") # Use self.logger
            return None # Indicate failure

    def add_image(self, filename: str, image_bytes: bytes = None, image_path: str = None, agent: str = None, tags: list = None) -> str | None:
        """Adds an image entry. Saves bytes if provided, otherwise copies from path."""
        if not image_bytes and not image_path:
            self.logger.error("add_image requires either image_bytes or image_path.") # Use self.logger
            return None
            
        entry_id = str(uuid.uuid4())
        # Use the provided filename directly, assuming it's unique enough or context-specific
        # Alternatively, prepend entry_id: filename = f"{entry_id}_{filename}" 
        save_path = self.base_path / filename
        
        try:
            # Ensure directory exists (redundant if __init__ worked, but safe)
            self.base_path.mkdir(parents=True, exist_ok=True)
            
            if image_bytes:
                # Save bytes directly
                with open(save_path, 'wb') as f:
                    f.write(image_bytes)
                self.logger.debug(f"Saved image bytes to {save_path}") # Use self.logger
            elif image_path:
                # Copy from existing path
                copy2(image_path, save_path)
                self.logger.debug(f"Copied image from {image_path} to {save_path}") # Use self.logger

            # Log metadata
            entry = {
                'id': entry_id,
                'type': 'image',
                'filename': filename,
                'path': str(save_path.relative_to(self.memory_root)), # Store path relative to memory root
                'mime': None,  # future: detect mime 
                'dimensions': None,  # future: detect with PIL
                'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
                'agent': agent,
                'tags': tags or []
            }
            with self.lock:
                with open(self.metadata_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(entry) + "\n")
            self.logger.debug(f"Added image entry {entry_id}") # Use self.logger
            return entry_id
            
        except IOError as e:
             self.logger.error(f"IOError saving image file {save_path}: {e}") # Use self.logger
        except Exception as e:
            self.logger.error(f"Error saving image or writing metadata for {filename}: {e}") # Use self.logger
            # Attempt cleanup if file was created but metadata failed
            if save_path.exists():
                try: save_path.unlink()
                except OSError: pass
        return None # Indicate failure
        
    def add_audio(self, filename: str, audio_bytes: bytes, agent: str = None, tags: list = None) -> str | None:
        """Saves audio bytes to a file within the agent's memory path and logs metadata."""
        entry_id = str(uuid.uuid4())
        # Use the provided filename directly
        save_path = self.base_path / filename 
        
        try:
            # Ensure directory exists
            self.base_path.mkdir(parents=True, exist_ok=True)
            
            # Save audio bytes
            with open(save_path, 'wb') as f:
                f.write(audio_bytes)
            self.logger.debug(f"Saved audio bytes to {save_path}") # Use self.logger

            # Log metadata
            entry = {
                'id': entry_id,
                'type': 'audio',
                'filename': filename,
                'path': str(save_path.relative_to(self.memory_root)), # Store path relative to memory root
                'format': Path(filename).suffix.lstrip('.'), # Infer format from extension
                'duration': None, # future: detect with soundfile/librosa
                'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
                'agent': agent,
                'tags': tags or []
            }
            with self.lock:
                with open(self.metadata_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(entry) + "\n")
            self.logger.debug(f"Added audio entry {entry_id}") # Use self.logger
            return entry_id
            
        except IOError as e:
             self.logger.error(f"IOError saving audio file {save_path}: {e}") # Use self.logger
        except Exception as e:
            self.logger.error(f"Error saving audio or writing metadata for {filename}: {e}") # Use self.logger
            # Attempt cleanup if file was created but metadata failed
            if save_path.exists():
                try: save_path.unlink()
                except OSError: pass
        return None # Indicate failure

    def get_entry(self, entry_id: str) -> dict | None:
        """Retrieve metadata entry by its ID from the central metadata file."""
        if not self.metadata_file.exists():
            return None
        try:
            # No lock needed for read usually, but safer if deletes happen often
            # with self.lock: 
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get('id') == entry_id:
                            # Add absolute path for convenience if needed by caller
                            if 'path' in entry:
                                entry['absolute_path'] = str(self.memory_root / entry['path'])
                            return entry
                    except json.JSONDecodeError:
                        self.logger.warning(f"Skipping malformed line in metadata file: {line.strip()}")
                        continue
        except Exception as e:
            self.logger.error(f"Error reading metadata file {self.metadata_file}: {e}")
        return None

    def delete_entry(self, entry_id: str) -> bool:
        """Deletes an entry's metadata and associated media file (if applicable)."""
        if not self.metadata_file.exists():
            self.logger.warning(f"Metadata file not found, cannot delete entry {entry_id}.")
            return False

        temp_metadata_path = self.metadata_file.with_suffix('.jsonl.tmp')
        deleted = False
        entry_to_delete = None

        try:
            with self.lock: # Ensure exclusive access for read-modify-write
                # First pass: Find the entry and check if a file needs deletion
                with open(self.metadata_file, 'r', encoding='utf-8') as src:
                    for line in src:
                        try:
                            entry = json.loads(line)
                            if entry.get('id') == entry_id:
                                entry_to_delete = entry
                                break # Found it
                        except json.JSONDecodeError:
                            continue
                
                if not entry_to_delete:
                    self.logger.warning(f"Entry ID {entry_id} not found for deletion.")
                    return False # Entry not found

                # Second pass: Rewrite the metadata file excluding the deleted entry
                with open(self.metadata_file, 'r', encoding='utf-8') as src, \
                     open(temp_metadata_path, 'w', encoding='utf-8') as dst:
                    for line in src:
                        try:
                            entry = json.loads(line)
                            if entry.get('id') != entry_id:
                                dst.write(line)
                            else:
                                deleted = True # Mark as successfully found for deletion
                        except json.JSONDecodeError:
                            dst.write(line) # Preserve malformed lines
                
                # Replace the original file with the temp file
                os.replace(temp_metadata_path, self.metadata_file)

            # If metadata rewrite was successful, delete the associated file (outside the lock)
            if deleted and 'path' in entry_to_delete and entry_to_delete.get('type') in ['image', 'audio']:
                file_path_relative = entry_to_delete['path']
                file_path_absolute = self.memory_root / file_path_relative
                if file_path_absolute.exists():
                    try:
                        file_path_absolute.unlink()
                        self.logger.info(f"Deleted associated file for entry {entry_id}: {file_path_absolute}")
                    except OSError as e:
                        self.logger.error(f"Error deleting file {file_path_absolute} for entry {entry_id}: {e}")
                        # Metadata was deleted, but file deletion failed. Logged error.
            
            if deleted:
                self.logger.info(f"Successfully deleted entry {entry_id} from metadata.")
            
            return deleted

        except Exception as e:
            self.logger.error(f"Error during delete_entry operation for {entry_id}: {e}", exc_info=True)
            # Clean up temp file if it exists after an error
            if temp_metadata_path.exists():
                try: temp_metadata_path.unlink()
                except OSError: pass
            return False

    def tag_entry(self, entry_id: str, tags: list) -> bool:
        """Adds tags to an existing entry by rewriting the metadata file."""
        if not self.metadata_file.exists():
            self.logger.warning(f"Metadata file not found, cannot tag entry {entry_id}.")
            return False
        if not isinstance(tags, list):
             self.logger.warning(f"Tags must be a list for entry {entry_id}.")
             return False

        temp_metadata_path = self.metadata_file.with_suffix('.jsonl.tmp')
        updated = False

        try:
            with self.lock: # Ensure exclusive access
                with open(self.metadata_file, 'r', encoding='utf-8') as src, \
                     open(temp_metadata_path, 'w', encoding='utf-8') as dst:
                    for line in src:
                        try:
                            entry = json.loads(line)
                            if entry.get('id') == entry_id:
                                current_tags = set(entry.get('tags', []))
                                new_tags = current_tags.union(set(tags)) # Add new tags, ensuring uniqueness
                                if new_tags != current_tags:
                                    entry['tags'] = sorted(list(new_tags)) # Store as sorted list
                                    dst.write(json.dumps(entry) + "\n")
                                    updated = True
                                    self.logger.info(f"Updated tags for entry {entry_id}")
                                else:
                                     dst.write(line) # No change, write original line
                            else:
                                dst.write(line) # Write other lines as is
                        except json.JSONDecodeError:
                            dst.write(line) # Preserve malformed lines
                
                # Replace the original file if updates were made
                if updated:
                    os.replace(temp_metadata_path, self.metadata_file)
                else:
                    # No updates needed, remove temp file
                    if temp_metadata_path.exists():
                        temp_metadata_path.unlink()
            
            return updated

        except Exception as e:
            self.logger.error(f"Error during tag_entry operation for {entry_id}: {e}", exc_info=True)
            # Clean up temp file if it exists after an error
            if temp_metadata_path.exists():
                try: temp_metadata_path.unlink()
                except OSError: pass
            return False

    def search(self, q: str = None, entry_type: str = None, tags: list = None, since: str = None) -> list:
        """Search stored metadata entries with optional filters."""
        results = []
        if not self.metadata_file.exists():
            return results
            
        since_dt = None
        if since:
            try:
                since_dt = datetime.datetime.fromisoformat(since.replace('Z', '+00:00'))
            except ValueError:
                self.logger.warning(f"Invalid ISO timestamp format for 'since': {since}. Ignoring time filter.")
                since_dt = None
        
        search_tags = set(tags) if tags else None

        try:
            # Use lock for read consistency if concurrent writes/deletes are frequent
            # with self.lock:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        
                        # --- Filtering Logic --- 
                        # Type filter
                        if entry_type and entry.get('type') != entry_type:
                            continue
                        # Timestamp filter
                        if since_dt:
                            entry_ts_str = entry.get('timestamp')
                            if entry_ts_str:
                                try:
                                    entry_dt = datetime.datetime.fromisoformat(entry_ts_str.replace('Z', '+00:00'))
                                    if entry_dt < since_dt:
                                        continue
                                except ValueError:
                                    pass # Ignore entries with bad timestamps if filtering
                            else:
                                continue # Skip entries without timestamp if filtering by time
                        # Tag filter (match all provided tags)
                        if search_tags and not search_tags.issubset(set(entry.get('tags', []))):
                            continue
                        # Query string filter (case-insensitive)
                        if q:
                            query_lower = q.lower()
                            match = False
                            if entry.get('type') == 'text' and query_lower in entry.get('data', '').lower():
                                match = True
                            elif entry.get('type') in ['image', 'audio'] and query_lower in entry.get('filename', '').lower():
                                match = True
                            # Optionally search tags too
                            elif any(query_lower in tag.lower() for tag in entry.get('tags', [])):
                                 match = True
                                 
                            if not match:
                                continue
                        # --- End Filtering --- 
                        
                        # Add absolute path if it's a media entry
                        if 'path' in entry:
                            entry['absolute_path'] = str(self.memory_root / entry['path'])
                            
                        results.append(entry)
                        
                    except json.JSONDecodeError:
                        self.logger.warning(f"Skipping malformed line during search: {line.strip()}")
                        continue
        except Exception as e:
            self.logger.error(f"Error searching memory metadata file {self.metadata_file}: {e}")
            
        # Optional: Sort results by timestamp descending?
        # results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return results

    def summarize_recent(self, n: int = 10) -> str:
        """Return a summary of the most recent n entries (stub)"""
        # Future implementation
        return ""

    def generate_report(self, output_path: str) -> None:
        """Export all entries to a markdown report (stub)"""
        # Future implementation
        pass

class OutcomeLogger:
    """Records rewards/outcomes for tasks/runs to a JSONL file and computes best performer."""
    def __init__(self, path):
        self.path = path
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def record(self, id, reward):
        """Append a reward record for a given id with timestamp."""
        entry = {
            "id": id,
            "reward": reward,
            "timestamp": datetime.datetime.utcnow().isoformat() + 'Z'
        }
        try:
            with open(self.path, 'a') as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"Error writing to OutcomeLogger path {self.path}: {e}")

    def best(self):
        """Compute which id has the highest average reward from the log file."""
        if not os.path.exists(self.path):
            return None
        stats = {}
        try:
            with open(self.path, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        _id = entry.get('id')
                        _reward = entry.get('reward', 0)
                        if _id is not None:
                            stats.setdefault(_id, []).append(_reward)
                    except json.JSONDecodeError:
                        continue
            if not stats:
                return None
            # calculate average rewards
            averages = {k: sum(v)/len(v) for k, v in stats.items() if v}
            # return id with highest average reward
            return max(averages, key=averages.get)
        except Exception as e:
            print(f"Error reading OutcomeLogger path {self.path}: {e}")
            return None

class SunsetPolicy:
    """Archives stale roadmap items based on due_date."""
    def __init__(self, path, archive_past_days=0):
        self.path = path
        self.archive_past_days = archive_past_days  # days past due date to archive

    def archive_stale(self) -> list:
        """Mark milestones past due_date by archive_past_days as 'archived'. Returns list of updated IDs."""
        archived = []
        if not os.path.exists(self.path):
            print(f"Error: Roadmap file not found at {self.path}")
            return archived
        try:
            with open(self.path, 'r') as f:
                data = json.load(f)
            changed = False
            today = datetime.datetime.utcnow().date()
            for goal in data:
                milestones = goal.get('milestones', [])
                for m in milestones:
                    due_str = m.get('due_date')
                    status = m.get('status')
                    if due_str and status != 'archived':
                        try:
                            due_date = datetime.datetime.fromisoformat(due_str).date()
                            if (today - due_date).days >= self.archive_past_days:
                                m['status'] = 'archived'
                                archived.append(m.get('id'))
                                changed = True
                        except ValueError:
                            continue
            if changed:
                temp = self.path + '.tmp'
                with open(temp, 'w') as f:
                    json.dump(data, f, indent=2)
                os.replace(temp, self.path)
            return archived
        except Exception as e:
            print(f"Error processing SunsetPolicy on {self.path}: {e}")
            return archived

@dataclass
class VerificationResult:
    is_valid: bool
    source: str        # 'wolfram' | 'heuristic' | 'llm'
    confidence: float  # 0.0 - 1.0
    details: str = ''
    error: str = None

class FactVerifier:
    """Verifies factual correctness of answers using WolframAlpha API or fallback heuristics."""
    def __init__(self, wolfram_app_id: str = None, fallback_confidence: float = 0.5):
        # Read from environment if not explicitly provided
        self.app_id = wolfram_app_id or os.getenv('WOLFRAM_APP_ID')
        self.fallback_confidence = fallback_confidence
        if not self.app_id:
            print("Warning: WOLFRAM_APP_ID not provided; using heuristic fallback.")

    def verify(self, question: str, answer: str) -> VerificationResult:
        """Return VerificationResult indicating validity of the answer."""
        # Use WolframAlpha if app_id available
        if self.app_id:
            try:
                url = 'http://api.wolframalpha.com/v2/query'
                params = {
                    'appid': self.app_id,
                    'input': f"Is the following answer correct for '{question}': {answer}?",
                    'output': 'JSON'
                }
                resp = requests.get(url, params=params, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    # Simple check: if Wolfram returned a result pod with solution interpretation
                    pods = data.get('queryresult', {}).get('pods', [])
                    is_valid = any(p.get('title', '').lower().startswith('result') for p in pods)
                    confidence = 0.9 if is_valid else 0.1
                    return VerificationResult(is_valid, 'wolfram', confidence)
                else:
                    return VerificationResult(False, 'wolfram', 0.0, error=f"HTTP {resp.status_code}")
            except Exception as e:
                return VerificationResult(False, 'wolfram', 0.0, error=str(e))
        # Fallback heuristic: simple keyword matching
        # For numeric answers, check if digits in answer
        if any(char.isdigit() for char in answer):
            return VerificationResult(True, 'heuristic', self.fallback_confidence)
        # Otherwise assume unknown
        return VerificationResult(False, 'heuristic', self.fallback_confidence)

# Note: For advanced usage, integrate LLM-based verification as another fallback source.

@dataclass
class TuningResult:
    best_params: dict
    best_score: float
    history: list

class SelfTuner:
    """Autonomous tuner for hyperparameters using simple random search and outcome logging."""
    def __init__(self, config_dir: str, logger=None):
        self.config_dir = config_dir
        os.makedirs(self.config_dir, exist_ok=True)
        self.logger = logger or OutcomeLogger(os.path.join(self.config_dir, 'tuner.log'))
        self.best_params = None
        self.best_score = float('-inf')
        self.history = []

    def tune(self, objective_fn, param_space: dict, trials: int = 10) -> TuningResult:
        """Run random search over param_space for a number of trials, returning best result."""
        for trial in range(trials):
            sampled = {k: random.choice(v) for k, v in param_space.items()}
            try:
                score = objective_fn(**sampled)
            except Exception:
                score = float('-inf')
            self.history.append({'params': sampled, 'score': score})
            self.logger.record(trial, score)
            if score > self.best_score:
                self.best_score = score
                self.best_params = sampled
        best_path = os.path.join(self.config_dir, 'best_params.json')
        with open(best_path, 'w') as f:
            json.dump(self.best_params or {}, f, indent=2)
        return TuningResult(self.best_params, self.best_score, self.history)

    def train_adapter(self, pairs, epochs: int = 1):
        """Placeholder: train an adapter using best_params from tune()."""
        # Future: implement adapter training logic
        pass

# CI/CD Tasks Agent
@dataclass
class PipelineResult:
    success: bool
    provider: str
    run_id: str = None
    status: str = None
    logs: str = None
    error: str = None

class CICDTasks:
    """Agent for triggering and monitoring CI/CD pipelines."""
    def __init__(self, provider: str = 'github_actions', config_path: str = None, token_env: str = 'GITHUB_TOKEN'):
        self.provider = provider
        self.config_path = config_path
        self.token = os.getenv(token_env)
        if not self.token:
            print(f"Warning: {token_env} not set; CI/CD triggers may fail.")

    def trigger(self, workflow_file: str = None, ref: str = 'main', inputs: dict = None) -> PipelineResult:
        """Trigger a new pipeline run. Returns PipelineResult with run_id."""
        # TODO: implement actual API call to trigger pipeline using self.provider
        return PipelineResult(False, self.provider, error="Not implemented")

    def status(self, run_id: str) -> PipelineResult:
        """Check the status of a pipeline run by run_id."""
        # TODO: implement status check via provider API
        return PipelineResult(False, self.provider, run_id=run_id, status="unknown", error="Not implemented")

    def fetch_logs(self, run_id: str) -> str:
        """Fetch logs for the given run_id."""
        # TODO: implement log retrieval from provider
        return ""

    def schedule(self, cron_expr: str, workflow_file: str = None):
        """Schedule a pipeline using a cron expression."""
        # TODO: schedule pipeline via provider cron or scheduler
        pass

class AgentRegistry:
    """Discovers, validates, and loads agents from a directory."""
    def __init__(self, agents_dir: str = "agents", schema_path: str = "schemas/agent.schema.json"):
        self.agents_dir = Path(agents_dir)
        self.schema_path = Path(schema_path)
        self.agents = {}
        self.schema = self._load_schema()
        if not self.schema:
            print(f"Error: Agent schema not found or invalid at {self.schema_path}")

    def _load_schema(self):
        if not self.schema_path.exists():
            return None
        try:
            with open(self.schema_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return None

    def discover(self):
        """Scan agents_dir, validate against schema, load agent classes, and store instances."""
        if not self.agents_dir.is_dir() or not self.schema:
            print(f"Error: Agents directory '{self.agents_dir}' not found or schema invalid.")
            return

        for config_file in self.agents_dir.glob("**/*.json"): # Assuming config files define agents
            agent_name = config_file.stem
            py_file = config_file.with_suffix(".py")
            if not py_file.exists():
                print(f"Warning: Python file not found for agent config '{config_file.name}'")
                continue

            try:
                with open(config_file, 'r') as f:
                    agent_config = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Invalid JSON in config file '{config_file.name}'")
                continue

            try:
                validate(instance=agent_config, schema=self.schema)
            except ValidationError as e:
                print(f"Warning: Schema validation failed for '{config_file.name}': {e.message}")
                continue

            try:
                # Construct module path relative to project root (adjust if needed)
                module_name = str(py_file.relative_to(Path.cwd()).with_suffix('')).replace(os.sep, '.')
                module = importlib.import_module(module_name)

                class_name = agent_config.get('class_name') # Assuming schema requires class_name
                if not class_name or not hasattr(module, class_name):
                    print(f"Warning: Class '{class_name}' not found in module '{module_name}'")
                    continue
                
                agent_class = getattr(module, class_name)
                self.agents[agent_name] = agent_class(config=agent_config)
                print(f"Successfully loaded agent: {agent_name}")
            except ImportError as e:
                 print(f"Warning: Failed to import module for agent '{agent_name}': {e}")
            except Exception as e:
                 print(f"Warning: Error loading agent '{agent_name}': {e}")

        print(f"Agent discovery complete. Loaded {len(self.agents)} agents.")
