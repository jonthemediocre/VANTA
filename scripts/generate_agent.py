#!/usr/bin/env python3
"""
CLI tool to generate new agents based on the A2A/MPC-compatible JSON schema.
Generates a stub in the 'agents/' directory and updates 'agents.index.mpc.json'.
"""
import os
import sys
import json
import argparse
from jsonschema import validate, ValidationError
from jinja2 import Environment, BaseLoader, select_autoescape

# Constants
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), '../schemas/agent.schema.json')
AGENTS_DIR = os.path.join(os.path.dirname(__file__), '../agents')
REGISTRY_PATH = os.path.join(os.path.dirname(__file__), '../agents.index.mpc.json')

# Jinja2 template for a new agent stub
AGENT_TEMPLATE = '''"""
Agent: {{ name }}
Type: {{ type }}
"""
import json
from ... import tools  # replace with actual tool imports

class {{ class_name }}:
    """Stub for agent '{{ name }}' of type '{{ type }}'."""
    def __init__(self, config: dict = None):
        self.config = config or {}

    def handle(self, context):
        """Main entrypoint for the agent."""
        # TODO: implement logic for intents: {{ intents|join(", ") }}
        pass
'''

def load_schema(path):
    with open(path, 'r') as f:
        return json.load(f)


def ensure_dirs():
    os.makedirs(AGENTS_DIR, exist_ok=True)
    if not os.path.exists(REGISTRY_PATH):
        with open(REGISTRY_PATH, 'w') as f:
            json.dump([], f, indent=2)


def parse_args():
    parser = argparse.ArgumentParser(description="Generate a new agent stub from schema")
    parser.add_argument('--name', required=True, help='Agent name (unique)')
    parser.add_argument('--type', required=True, help="Agent type, e.g. 'code_assistant'")
    parser.add_argument('--intents', required=True, help='Comma-separated list of intents')
    parser.add_argument('--entrypoint', required=True, help='Filename for the stub (e.g. my_agent.py)')
    parser.add_argument('--triggers', default='', help='Comma-separated triggers (onFileChange,onUserQuery,...)')
    parser.add_argument('--tools', default='', help='Comma-separated tool ids')
    parser.add_argument('--core', action='store_true', help='Mark as core agent with API exposure')
    parser.add_argument('--api-path', help='API endpoint path if core agent')
    parser.add_argument('--api-methods', default='GET', help='Comma-separated HTTP methods for API')
    return parser.parse_args()


def main():
    # Load and validate arguments
    args = parse_args()
    schema = load_schema(os.path.abspath(SCHEMA_PATH))
    # Build agent definition dict
    agent_def = {
        'name': args.name,
        'type': args.type,
        'intents': [i.strip() for i in args.intents.split(',') if i.strip()],
        'triggers': {t.strip(): True for t in args.triggers.split(',') if t.strip()},
        'entrypoint': os.path.join('agents', args.entrypoint),
        'tools': [t.strip() for t in args.tools.split(',') if t.strip()],
        'config': {}
    }
    if args.core:
        agent_def['core'] = True
        api_config = {'methods': [m.strip().upper() for m in args.api_methods.split(',')]}
        if args.api_path:
            api_config['path'] = args.api_path
        agent_def['api'] = api_config

    # Validate against schema
    try:
        validate(instance=agent_def, schema=schema)
    except ValidationError as ve:
        print(f"Schema validation error: {ve.message}")
        sys.exit(1)

    # Ensure directories and registry
    ensure_dirs()

    # Render agent stub
    class_name = ''.join([part.capitalize() for part in args.name.split('_')])
    env = Environment(loader=BaseLoader(), autoescape=select_autoescape())
    template = env.from_string(AGENT_TEMPLATE)
    stub_code = template.render(
        name=args.name,
        type=args.type,
        intents=agent_def['intents'],
        class_name=class_name
    )
    # Write stub file
    stub_path = os.path.join(AGENTS_DIR, args.entrypoint)
    with open(stub_path, 'w') as f:
        f.write(stub_code)
    print(f"Generated agent stub at {stub_path}")

    # Update registry
    registry = []
    with open(REGISTRY_PATH, 'r') as f:
        registry = json.load(f)
    registry.append(agent_def)
    with open(REGISTRY_PATH, 'w') as f:
        json.dump(registry, f, indent=2)
    print(f"Updated registry at {REGISTRY_PATH}")


if __name__ == '__main__':
    main() 