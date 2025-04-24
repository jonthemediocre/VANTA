import yaml
from pathlib import Path

framework_root = Path("FrAmEwOrK/agents/core")

def list_agents():
    # Ensure the directory exists to avoid errors if it hasn't been created yet
    if not framework_root.exists():
        print(f"Agent configuration directory not found: {framework_root}")
        return
    
    # Check if any YAML files exist
    yaml_files = list(framework_root.glob("*.yaml"))
    if not yaml_files:
        print(f"No YAML agent configuration files found in: {framework_root}")
        return

    for file in yaml_files:
        try:
            with open(file, "r") as f:
                print(f"\n--- {file.stem} ---")
                # Try to load and dump YAML for better formatting, fallback to raw read
                try:
                    content = yaml.safe_load(f)
                    # Reset file pointer to read again for raw print if needed
                    f.seek(0) 
                    if content: # Print YAML structure if load succeeds
                         print(yaml.dump(content, indent=2))
                    else: # Print raw if file is empty or not valid YAML
                         print(f.read())
                except yaml.YAMLError:
                     # Reset file pointer before reading raw content
                    f.seek(0) 
                    print(f.read()) # Print raw content if YAML parsing fails
        except Exception as e:
            print(f"Error reading file {file}: {e}")


if __name__ == "__main__":
    print("Loading VANTA agents...")
    list_agents() 