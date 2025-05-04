# === lora_manager.py ===

"""
LoraManager
Handles loading and managing LoRA (Low Rank Adaptation) models for context injection.
"""

import os
import yaml

class LoraManager:
    def __init__(self, config_file_path):
        self.config_file = config_file_path or 'templates/lora.yaml'
        self.loras = {}
        print("LoraManager initialized.")

    def load(self):
        abs_path = os.path.abspath(self.config_file)
        print(f"LoraManager → Loading LoRA config from: {abs_path}")

        try:
            if not os.path.exists(abs_path):
                print(f"  ⚠️ LoRA config file not found: {abs_path}. Using empty list.")
                self.loras = {}
                return

            with open(abs_path, 'r') as f:
                self.loras = yaml.safe_load(f) or {}
            print("  ✅ Loaded LoRA configurations.")
        except Exception as e:
            print(f"  ⚠️ Error loading LoRA configuration → {e}")
            self.loras = {}

    def list_available_loras(self):
        """
        List all available LoRAs from configuration.
        """
        return list(self.loras.keys())

    def get_lora_config(self, name):
        """
        Retrieve configuration for a specific LoRA.
        """
        return self.loras.get(name)
