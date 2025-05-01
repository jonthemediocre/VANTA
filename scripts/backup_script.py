import argparse
import sys
import os
from pathlib import Path
import logging

# Add project root to sys.path to allow importing vanta_seed
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

try:
    from vanta_seed.utils.mutation_manager import MutationManager
except ImportError:
    print("ERROR: Could not import MutationManager. Ensure vanta_seed is in the Python path.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BackupScript")

def main():
    parser = argparse.ArgumentParser(description="Create a backup of a VANTA instance.")
    parser.add_argument("instance_name", help="The name of the instance (e.g., 'instance_a', 'instance_b')")
    parser.add_argument("instance_path", help="The root path to the instance directory.")
    parser.add_argument("--archive-dir", default="./archive", help="Directory to store backups (default: ./archive)")
    parser.add_argument("--backup-id", default="manual_backup", help="An identifier for this backup (default: manual_backup)")

    args = parser.parse_args()

    instance_path = Path(args.instance_path).resolve()
    archive_dir = Path(args.archive_dir).resolve()

    if not instance_path.is_dir():
        logger.error(f"Instance path is not a valid directory: {instance_path}")
        sys.exit(1)
        
    # MutationManager needs a log file path, but we don't use logging functionality here
    # Provide a dummy path
    dummy_log_path = instance_path / "dummy_backup_log.yaml" 

    try:
        # We only need the backup functionality from MutationManager
        manager = MutationManager(
            instance_name=args.instance_name,
            instance_root_path=instance_path,
            log_file=dummy_log_path, # Not used for backup action
            archive_dir=archive_dir
        )
        
        backup_file = manager.create_backup(args.backup_id)
        
        if backup_file:
            logger.info(f"Backup successful: {backup_file}")
            sys.exit(0)
        else:
            logger.error("Backup failed.")
            sys.exit(1)

    except ValueError as e:
        logger.error(f"Initialization error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 