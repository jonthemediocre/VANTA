"""
VANTA Seed → Audit Logger
Logs structured audit events to file (and optionally console).
"""

import logging
import os

class AuditLogger:
    def __init__(self, config):
        self.config = config
        log_file = config.get_nested('logging', 'audit_log_file', 'vanta_audit.log')
        log_level_str = config.get_nested('logging', 'audit_log_level', 'INFO').upper()
        log_level = getattr(logging, log_level_str, logging.INFO)

        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
                print(f"📂 Created log directory: {log_dir}")
            except OSError as e:
                print(f"⚠️ Could not create log directory {log_dir}: {e}. Logging to current directory.")
                log_file = os.path.basename(log_file)

        self.logger = logging.getLogger('VantaAudit')
        self.logger.setLevel(log_level)

        # Prevent multiple handlers
        if not self.logger.handlers:
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

            # File handler
            try:
                fh = logging.FileHandler(log_file)
                fh.setLevel(log_level)
                fh.setFormatter(formatter)
                self.logger.addHandler(fh)
            except Exception as e:
                print(f"⚠️ Failed to set up file handler: {e}")

            # Optional console handler
            if config.get_nested('logging', 'audit_log_to_console', False):
                ch = logging.StreamHandler()
                ch.setLevel(log_level)
                ch.setFormatter(formatter)
                self.logger.addHandler(ch)

        print(f"✅ AuditLogger initialized → File: {log_file}, Level: {log_level_str}")

    def log_event(self, event_type, details):
        """
        Log a structured audit event.
        """
        log_message = f"Event: {event_type} | Details: {details}"
        self.logger.info(log_message)

