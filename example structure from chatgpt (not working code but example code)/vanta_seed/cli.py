# vanta_seed/cli.py

"""
Command-line interface for VantaSeed.
Routes command-line arguments into VantaSeed core operations.
"""

import argparse
from .core import VantaSeed


def main():
    parser = argparse.ArgumentParser(description="VantaSeed CLI - Modular Agent Kernel")
    parser.add_argument("command", choices=["start", "status", "rituals", "solve", "swarm"], help="Command to execute")
    parser.add_argument("--config", type=str, default="templates/config.yaml", help="Path to configuration file")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for the command")

    args = parser.parse_args()

    seed = VantaSeed(config_path=args.config)

    if args.command == "start":
        seed.start()

    elif args.command == "status":
        print("VantaSeed Status:")
        print(seed.describe_status())

    elif args.command == "rituals":
        print("Available Rituals:")
        rituals = seed.ritual_executor.list_rituals()
        for ritual in rituals:
            print(f"- {ritual.get('name')} (Trigger: {ritual.get('trigger_type')})")

    elif args.command == "solve":
        task = " ".join(args.args)
        result = seed.agentic_router.route(task_type="solve", task_content=task)
        print("Solve result:")
        print(result)

    elif args.command == "swarm":
        task = " ".join(args.args)
        result = seed.swarm_coordinator.aggregate(task)
        print("Swarm result:")
        print(result)

    else:
        print(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
