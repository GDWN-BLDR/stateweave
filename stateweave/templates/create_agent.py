#!/usr/bin/env python3
"""
create-stateweave-agent — Generate a new agent project with StateWeave pre-wired.
===================================================================================
Creates a ready-to-run agent project with:
- StateWeave adapters pre-configured
- Checkpoint store set up
- Export/import scripts included
- CI workflow with StateWeave validation

Usage:
    python -m stateweave.templates.create_agent my-agent --framework langgraph
"""

import argparse
import os
import sys
from pathlib import Path


AGENT_TEMPLATE = '''#!/usr/bin/env python3
"""
{agent_name} — Agent with StateWeave state portability.
"""

from stateweave.middleware import auto_checkpoint


@auto_checkpoint(every_n_steps=5, agent_id="{agent_id}")
def run_agent(payload):
    """Run the agent and return updated state.

    StateWeave auto-checkpoints every 5 steps.
    """
    # Your agent logic here
    return payload


if __name__ == "__main__":
    print("🧶 {agent_name} with StateWeave")
    print("  Run: stateweave doctor")
    print("  Export: stateweave export -f {framework} -a {agent_id} -o state.json")
    print("  History: stateweave history {agent_id}")
'''

EXPORT_SCRIPT = '''#!/usr/bin/env python3
"""Export agent state to a portable format."""

from stateweave.adapters import ADAPTER_REGISTRY
from stateweave.core.serializer import StateWeaveSerializer

FRAMEWORK = "{framework}"
AGENT_ID = "{agent_id}"

adapter_cls = ADAPTER_REGISTRY[FRAMEWORK]
adapter = adapter_cls()

payload = adapter.export_state(AGENT_ID)

serializer = StateWeaveSerializer(pretty=True)
print(serializer.dumps(payload).decode())
'''

REQUIREMENTS = '''stateweave>=0.3.0
'''

CI_WORKFLOW = '''name: Agent CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: stateweave doctor
      - uses: GDWN-BLDR/stateweave-action@v1
        with:
          validate: true
          diff-on-pr: true
'''

README_TEMPLATE = '''# {agent_name}

Agent project with [StateWeave](https://github.com/GDWN-BLDR/stateweave) state portability.

## Quick Start

```bash
pip install -r requirements.txt
python agent.py
```

## StateWeave Commands

```bash
# Check setup
stateweave doctor

# Export state
stateweave export -f {framework} -a {agent_id} -o state.json

# View checkpoint history
stateweave history {agent_id}

# Roll back to a previous state
stateweave rollback {agent_id} 3 -o restored.json
```
'''


def create_project(
    name: str,
    framework: str = "langgraph",
    output_dir: str = ".",
) -> dict:
    """Create a new agent project with StateWeave pre-wired.

    Args:
        name: Project/agent name.
        framework: Target framework.
        output_dir: Where to create the project directory.

    Returns:
        Dict with created file paths.
    """
    agent_id = name.lower().replace(" ", "-").replace("_", "-")
    project_dir = Path(output_dir) / name
    project_dir.mkdir(parents=True, exist_ok=True)

    # Create .github/workflows
    workflows_dir = project_dir / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)

    files = {}

    # agent.py
    agent_path = project_dir / "agent.py"
    agent_path.write_text(AGENT_TEMPLATE.format(
        agent_name=name, agent_id=agent_id, framework=framework,
    ))
    files["agent"] = str(agent_path)

    # export.py
    export_path = project_dir / "export.py"
    export_path.write_text(EXPORT_SCRIPT.format(
        framework=framework, agent_id=agent_id,
    ))
    files["export"] = str(export_path)

    # requirements.txt
    req_path = project_dir / "requirements.txt"
    req_path.write_text(REQUIREMENTS)
    files["requirements"] = str(req_path)

    # .github/workflows/ci.yml
    ci_path = workflows_dir / "ci.yml"
    ci_path.write_text(CI_WORKFLOW)
    files["ci"] = str(ci_path)

    # README.md
    readme_path = project_dir / "README.md"
    readme_path.write_text(README_TEMPLATE.format(
        agent_name=name, agent_id=agent_id, framework=framework,
    ))
    files["readme"] = str(readme_path)

    return {"project_dir": str(project_dir), "files": files}


def main():
    parser = argparse.ArgumentParser(
        prog="create-stateweave-agent",
        description="Create a new agent project with StateWeave pre-wired",
    )
    parser.add_argument("name", help="Project name")
    parser.add_argument(
        "--framework", "-f", default="langgraph",
        help="Target framework (default: langgraph)",
    )
    parser.add_argument(
        "--output-dir", "-o", default=".",
        help="Output directory (default: current directory)",
    )

    args = parser.parse_args()
    result = create_project(args.name, args.framework, args.output_dir)

    print(f"✓ Created StateWeave agent project: {result['project_dir']}")
    for label, path in result["files"].items():
        print(f"  → {path}")
    print()
    print(f"  cd {result['project_dir']}")
    print(f"  pip install -r requirements.txt")
    print(f"  stateweave doctor")


if __name__ == "__main__":
    main()
