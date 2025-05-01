import logging
import yaml
import datetime
import subprocess
import os
from pathlib import Path
import shutil
import zipfile

# Attempt to import GitPython, provide guidance if missing
try:
    import git
except ImportError:
    git = None
    logging.warning("GitPython not found. Git operations will use subprocess calls or be skipped.")

logger = logging.getLogger(__name__)

class MutationManager:
    """Handles logging, Git interactions, and backups for code mutations."""

    def __init__(self, instance_name: str, instance_root_path: str | Path, log_file: str | Path, archive_dir: str | Path):
        self.instance_name = instance_name
        self.root_path = Path(instance_root_path)
        self.log_path = Path(log_file)
        self.archive_dir = Path(archive_dir)
        
        if not self.root_path.is_dir():
            raise ValueError(f"Instance root path does not exist or is not a directory: {self.root_path}")
            
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Git Repo object if possible
        self.repo = None
        if git and (self.root_path / ".git").exists():
            try:
                self.repo = git.Repo(self.root_path)
                logger.info(f"Initialized Git repo for {self.instance_name} at {self.root_path}")
            except Exception as e:
                logger.error(f"Failed to initialize Git repo for {self.instance_name}: {e}")
        elif not git:
             logger.warning(f"GitPython not installed, Git operations will be limited for {self.instance_name}.")
        else:
             logger.warning(f"No .git directory found at {self.root_path} for {self.instance_name}. Git operations skipped.")


    def log_mutation_event(self, event_data: dict):
        """Appends a mutation event to the YAML log file."""
        try:
            log_entry = {
                'timestamp': datetime.datetime.now().isoformat(),
                'instance': self.instance_name,
                **event_data # Merge event data
            }
            
            current_log = []
            if self.log_path.exists():
                with open(self.log_path, 'r') as f:
                    try:
                        # Use safe_load_all if multiple YAML docs are possible
                        loaded_data = yaml.safe_load(f)
                        if isinstance(loaded_data, list):
                            current_log = loaded_data
                        elif loaded_data is not None: # Handle case where file might be empty or invalid
                            current_log = [loaded_data] 
                    except yaml.YAMLError as e:
                        logger.error(f"Error reading existing mutation log {self.log_path}: {e}")
                        # Decide recovery strategy: overwrite, backup and overwrite, or fail?
                        # For now, we'll append anyway, potentially creating mixed format
                        
            current_log.append(log_entry)
            
            with open(self.log_path, 'w') as f:
                yaml.dump(current_log, f, default_flow_style=False, sort_keys=False)
                
            logger.info(f"Logged mutation event {event_data.get('id', '')} to {self.log_path}")

        except Exception as e:
            logger.error(f"Failed to log mutation event to {self.log_path}: {e}", exc_info=True)

    def create_backup(self, backup_id: str) -> Path | None:
        """Creates a zip archive of the instance root directory."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{self.instance_name}_{backup_id}_{timestamp}.zip"
        backup_path = self.archive_dir / backup_name
        
        logger.info(f"Creating backup for {self.instance_name} (ID: {backup_id}) to {backup_path}...")
        
        try:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(self.root_path):
                    # Avoid zipping the archive directory itself or git internals if desired
                    if Path(root).resolve() == self.archive_dir.resolve():
                        continue
                    if '.git' in dirs:
                        dirs.remove('.git') # Don't zip .git by default
                        
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(self.root_path)
                        zipf.write(file_path, arcname)
            
            logger.info(f"Backup created successfully: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to create backup {backup_path}: {e}", exc_info=True)
            return None
            
    def commit_changes(self, message: str, files_to_add: list[str] = None) -> str | None:
        """Commits changes in the instance's Git repository."""
        if not self.repo:
            logger.warning(f"Cannot commit changes for {self.instance_name}, Git repository not available.")
            # Fallback using subprocess? Requires git CLI to be installed and configured.
            # try: 
            #     if files_to_add:
            #         subprocess.run(["git", "add"] + files_to_add, cwd=self.root_path, check=True)
            #     else: # Add all changes
            #         subprocess.run(["git", "add", "."], cwd=self.root_path, check=True)
            #     result = subprocess.run(["git", "commit", "-m", message], cwd=self.root_path, check=True, capture_output=True, text=True)
            #     logger.info(f"Subprocess Git commit successful for {self.instance_name}")
            #     # How to get commit hash reliably? Might need further parsing.
            #     return "subprocess_commit_success" # Placeholder
            # except Exception as e:
            #     logger.error(f"Subprocess Git commit failed for {self.instance_name}: {e}")
            #     return None
            return None

        try:
            if files_to_add:
                # Convert relative paths if needed
                paths_to_add = [str(self.root_path / f) if not Path(f).is_absolute() else f for f in files_to_add]
                self.repo.index.add(paths_to_add)
                logger.debug(f"Added specific files to index: {paths_to_add}")
            else:
                # Add all tracked changes
                self.repo.git.add(update=True) # Stages modified/deleted tracked files
                self.repo.index.add(self.repo.untracked_files) # Stages new untracked files
                logger.debug(f"Added all tracked changes and untracked files to index.")

            if not self.repo.index.diff("HEAD"):
                 logger.info(f"No changes to commit for {self.instance_name}.")
                 return self.repo.head.commit.hexsha # Return current head hash

            commit = self.repo.index.commit(message)
            logger.info(f"Committed changes for {self.instance_name}: {commit.hexsha} - {message}")
            return commit.hexsha
        except Exception as e:
            logger.error(f"Git commit failed for {self.instance_name}: {e}", exc_info=True)
            return None

    def create_branch(self, branch_name: str, base_branch: str = 'main'):
        """Creates a new branch from a base branch."""
        if not self.repo:
             logger.warning(f"Cannot create branch for {self.instance_name}, Git repo not available.")
             return False
        try:
            # Ensure base branch exists
            if base_branch not in self.repo.heads:
                 logger.error(f"Base branch '{base_branch}' does not exist.")
                 return False
                 
            # Check if target branch already exists
            if branch_name in self.repo.heads:
                 logger.warning(f"Branch '{branch_name}' already exists. Checking it out.")
                 self.repo.heads[branch_name].checkout()
            else:
                 new_branch = self.repo.create_head(branch_name, self.repo.heads[base_branch].commit)
                 new_branch.checkout()
                 logger.info(f"Created and checked out new branch '{branch_name}' from '{base_branch}' for {self.instance_name}.")
            return True
        except Exception as e:
             logger.error(f"Failed to create or checkout branch '{branch_name}': {e}", exc_info=True)
             return False
             
    def merge_branch(self, source_branch: str, target_branch: str = 'main', strategy_option='ours'):
         """Merges source branch into target branch. Handle with care!"""
         if not self.repo:
              logger.warning(f"Cannot merge branch for {self.instance_name}, Git repo not available.")
              return False
         try:
              original_branch = self.repo.active_branch
              # Checkout target branch
              if target_branch not in self.repo.heads:
                   logger.error(f"Target branch '{target_branch}' does not exist.")
                   return False
              self.repo.heads[target_branch].checkout()
              logger.info(f"Checked out target branch '{target_branch}'.")

              # Check if source branch exists
              if source_branch not in self.repo.heads:
                   logger.error(f"Source branch '{source_branch}' does not exist.")
                   # Checkout back to original branch before failing
                   original_branch.checkout()
                   return False
                   
              # Perform the merge
              logger.info(f"Merging '{source_branch}' into '{target_branch}' with strategy '{strategy_option}'...")
              # Use Git command for strategy options
              merge_base = self.repo.merge_base(self.repo.heads[target_branch], self.repo.heads[source_branch])
              self.repo.index.merge_tree(self.repo.heads[source_branch], base=merge_base) 
              # Use specified strategy option if conflicts arise (e.g., 'ours', 'theirs')
              commit_message = f"Merge branch '{source_branch}' into {target_branch}"
              self.repo.index.commit(commit_message, parent_commits=(self.repo.heads[target_branch].commit, self.repo.heads[source_branch].commit))
              
              logger.info(f"Merge successful. New commit on '{target_branch}'.")
              # Checkout back to the original branch? Or stay on target? Staying on target for now.
              # original_branch.checkout() 
              return True

         except git.GitCommandError as e:
              logger.error(f"Git merge failed: {e}. Conflicts likely occurred.", exc_info=True)
              # Attempt to abort merge on failure
              try:
                   self.repo.git.merge('--abort')
                   logger.info("Attempted to abort failed merge.")
              except Exception as abort_e:
                   logger.error(f"Failed to abort merge: {abort_e}")
              # Checkout back to original branch
              if original_branch:
                  original_branch.checkout()
              return False
         except Exception as e:
              logger.error(f"Failed to merge branch '{source_branch}' into '{target_branch}': {e}", exc_info=True)
              if original_branch:
                  original_branch.checkout() # Ensure we go back if something else fails
              return False

# Example Usage (Illustrative)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Testing MutationManager...")
    
    # Create dummy instance dirs and files for testing
    DUMMY_ROOT_A = Path("./dummy_instance_a")
    DUMMY_ROOT_B = Path("./dummy_instance_b")
    ARCHIVE_DIR = Path("./dummy_archive")
    
    for p in [DUMMY_ROOT_A, DUMMY_ROOT_B, ARCHIVE_DIR]:
         shutil.rmtree(p, ignore_errors=True)
         p.mkdir(parents=True, exist_ok=True)
         
    # Create dummy files
    (DUMMY_ROOT_A / "main.py").write_text("print('Hello from A')")
    (DUMMY_ROOT_A / "utils.py").write_text("def helper_a(): pass")
    (DUMMY_ROOT_A / "mutations.yaml").touch()

    # Initialize dummy git repo
    if git:
        try:
             repo_a = git.Repo.init(DUMMY_ROOT_A)
             repo_a.index.add(["main.py", "utils.py", "mutations.yaml"])
             repo_a.index.commit("Initial commit for A")
             logger.info(f"Initialized dummy git repo at {DUMMY_ROOT_A}")
        except Exception as e:
             logger.error(f"Failed to init dummy repo A: {e}")
             git = None # Disable git ops if init fails
    
    # Setup managers
    manager_a = MutationManager("instance_a", DUMMY_ROOT_A, DUMMY_ROOT_A / "mutations.yaml", ARCHIVE_DIR)
    # manager_b = MutationManager("instance_b", DUMMY_ROOT_B, DUMMY_ROOT_B / "mutations.yaml", ARCHIVE_DIR) # If needed
    
    # Test logging
    event1 = {'id': 'mut001', 'type': 'request', 'from': 'User', 'target_file': 'main.py'}
    manager_a.log_mutation_event(event1)
    
    # Test backup
    backup_path = manager_a.create_backup("mut001_pre")
    print(f"Backup created at: {backup_path}")
    
    # Test commit (simulate change)
    (DUMMY_ROOT_A / "main.py").write_text("print('Hello from modified A')")
    commit_hash = manager_a.commit_changes("Simulated modification mut001", files_to_add=["main.py"])
    print(f"Commit hash: {commit_hash}")

    # Test logging again
    event2 = {'id': 'mut001', 'type': 'complete', 'commit': commit_hash, 'backup': str(backup_path)}
    manager_a.log_mutation_event(event2)

    # Test Branching and Merging (if git available)
    if manager_a.repo:
         print("--- Testing Branching --- ")
         created = manager_a.create_branch("dev-b")
         if created:
              (DUMMY_ROOT_A / "new_feature.py").write_text("# Feature B")
              dev_commit = manager_a.commit_changes("Add feature B on dev-b", files_to_add=["new_feature.py"])
              print(f"Commit on dev-b: {dev_commit}")
              
              print("--- Testing Merging --- ")
              merged = manager_a.merge_branch(source_branch="dev-b", target_branch="main")
              print(f"Merge successful: {merged}")
              if merged:
                   print(f"Main branch HEAD: {manager_a.repo.heads.main.commit.hexsha}")
                   print(f"Files in main branch root: {[item.name for item in DUMMY_ROOT_A.iterdir()]}")
                   
    print("MutationManager tests complete.")
    # Clean up dummy dirs
    # shutil.rmtree(DUMMY_ROOT_A, ignore_errors=True)
    # shutil.rmtree(DUMMY_ROOT_B, ignore_errors=True)
    # shutil.rmtree(ARCHIVE_DIR, ignore_errors=True) 