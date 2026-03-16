"""
Adapter Generator — Scaffold new framework adapters with tests and docs.
==========================================================================
This is Flywheel Feature #3 — reduces contribution friction from
"read the codebase" to "fill in 4 methods".

Usage:
    stateweave generate-adapter my-framework
    # Creates:
    #   stateweave/adapters/my_framework_adapter.py
    #   tests/unit/test_my_framework_adapter.py
"""

import logging
import os
from typing import Any, Dict

logger = logging.getLogger("stateweave.core.generator")

ADAPTER_TEMPLATE = '''"""
{framework_title} Adapter — Translates {framework_title} agent state ↔ Universal Schema.
{separator}
Maps {framework_title}'s internal state representation
to the StateWeave Universal Schema for cross-framework portability.

TODO: Fill in the state extraction and translation logic for {framework_title}.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from stateweave.adapters.base import ExportError, ImportError_, StateWeaveAdapter
from stateweave.schema.v1 import (
    AccessPolicy,
    AgentInfo,
    AgentMetadata,
    AuditAction,
    AuditEntry,
    CognitiveState,
    Message,
    MessageRole,
    NonPortableWarning,
    NonPortableWarningSeverity,
    StateWeavePayload,
    ToolResult,
)

logger = logging.getLogger("stateweave.adapters.{framework_name}")

{framework_upper}_TARGET_VERSION = "0.1.x"

# Role mapping: {framework_title} roles → Universal Schema
{framework_upper}_ROLE_MAP: Dict[str, MessageRole] = {{
    "user": MessageRole.HUMAN,
    "assistant": MessageRole.ASSISTANT,
    "system": MessageRole.SYSTEM,
    "tool": MessageRole.TOOL,
}}

UNIVERSAL_TO_{framework_upper}_ROLE: Dict[MessageRole, str] = {{
    MessageRole.HUMAN: "user",
    MessageRole.ASSISTANT: "assistant",
    MessageRole.SYSTEM: "system",
    MessageRole.TOOL: "tool",
}}


class {class_name}(StateWeaveAdapter):
    """{framework_title} adapter for StateWeave.

    TODO: Implement the 4 required methods:
      1. framework_name → str
      2. export_state(agent_id) → StateWeavePayload
      3. import_state(payload) → Any
      4. list_agents() → List[AgentInfo]

    Usage:
        adapter = {class_name}(agent=my_agent)
        payload = adapter.export_state("my-agent")
    """

    def __init__(self, agent: Optional[Any] = None):
        """Initialize the {framework_title} adapter.

        Args:
            agent: A {framework_title} agent instance.
        """
        self._agent = agent
        self._agents: Dict[str, Dict[str, Any]] = {{}}

    @property
    def framework_name(self) -> str:
        return "{framework_name}"

    def export_state(self, agent_id: str, **kwargs) -> StateWeavePayload:
        """Export {framework_title} agent state to Universal Schema.

        TODO: Implement state extraction from {framework_title}.
        """
        try:
            state = self._extract_state()
        except Exception as e:
            raise ExportError(
                f"Failed to get {framework_title} state for '{{agent_id}}': {{e}}"
            ) from e

        cognitive_state = self._translate_to_cognitive_state(state)
        warnings = self._detect_non_portable(state)

        metadata = AgentMetadata(
            agent_id=agent_id,
            agent_name=kwargs.get("agent_name", f"{framework_name}-{{agent_id}}"),
            namespace=kwargs.get("namespace", "default"),
            tags=kwargs.get("tags", ["{framework_name}"]),
            access_policy=AccessPolicy.PRIVATE,
            framework_capabilities={{}},
        )

        audit_trail = [
            AuditEntry(
                timestamp=datetime.utcnow(),
                action=AuditAction.EXPORT,
                framework="{framework_name}",
                success=True,
                details={{"agent_id": agent_id}},
            )
        ]

        return StateWeavePayload(
            source_framework="{framework_name}",
            source_version={framework_upper}_TARGET_VERSION,
            exported_at=datetime.utcnow(),
            cognitive_state=cognitive_state,
            metadata=metadata,
            audit_trail=audit_trail,
            non_portable_warnings=warnings,
        )

    def import_state(self, payload: StateWeavePayload, **kwargs) -> Any:
        """Import a StateWeavePayload into {framework_title}.

        TODO: Implement state restoration for {framework_title}.
        """
        target_id = kwargs.get("agent_id", payload.metadata.agent_id)

        try:
            state_dict = self._translate_from_cognitive_state(
                payload.cognitive_state
            )
            self._agents[target_id] = state_dict

            logger.info(
                f"Imported state into {framework_title} agent '{{target_id}}' "
                f"(from {{payload.source_framework}})"
            )

            return {{
                "agent_id": target_id,
                "framework": "{framework_name}",
                "state_keys": list(state_dict.keys()),
                "import_source": payload.source_framework,
            }}
        except Exception as e:
            raise ImportError_(
                f"Failed to import into {framework_title} '{{target_id}}': {{e}}"
            ) from e

    def list_agents(self) -> List[AgentInfo]:
        """List all known {framework_title} agents."""
        agents = []
        for agent_id in self._agents:
            agents.append(
                AgentInfo(
                    agent_id=agent_id,
                    agent_name=f"{framework_name}-{{agent_id}}",
                    framework="{framework_name}",
                    metadata={{"source": "local_store"}},
                )
            )
        return agents

    def _extract_state(self) -> Dict[str, Any]:
        """Extract state from {framework_title} agent.

        TODO: Implement framework-specific state extraction.
        """
        return {{}}

    def _translate_to_cognitive_state(
        self, state: Dict[str, Any]
    ) -> CognitiveState:
        """Translate {framework_title} state to CognitiveState.

        TODO: Map {framework_title} state fields to Universal Schema fields.
        """
        return CognitiveState()

    def _translate_from_cognitive_state(
        self, cognitive_state: CognitiveState
    ) -> Dict[str, Any]:
        """Translate CognitiveState to {framework_title} state.

        TODO: Map Universal Schema fields back to {framework_title} format.
        """
        return {{}}

    def _detect_non_portable(
        self, state: Dict[str, Any]
    ) -> List[NonPortableWarning]:
        """Detect {framework_title}-specific non-portable elements.

        TODO: Add warnings for framework-specific state that won't transfer.
        """
        return []
'''

TEST_TEMPLATE = '''"""Tests for {framework_title} adapter."""

import pytest

from stateweave.adapters.{framework_name}_adapter import {class_name}
from stateweave.schema.v1 import (
    AgentMetadata,
    CognitiveState,
    Message,
    MessageRole,
    StateWeavePayload,
)


class Test{class_name}:
    """Test suite for {class_name}."""

    def test_framework_name(self):
        adapter = {class_name}()
        assert adapter.framework_name == "{framework_name}"

    def test_export_state_basic(self):
        adapter = {class_name}()
        payload = adapter.export_state("test-agent")
        assert payload.source_framework == "{framework_name}"
        assert payload.metadata.agent_id == "test-agent"

    def test_import_state_basic(self):
        adapter = {class_name}()
        payload = StateWeavePayload(
            source_framework="test",
            metadata=AgentMetadata(agent_id="test-agent"),
            cognitive_state=CognitiveState(
                conversation_history=[
                    Message(role=MessageRole.HUMAN, content="Hello"),
                ],
            ),
        )
        result = adapter.import_state(payload)
        assert result["framework"] == "{framework_name}"

    def test_round_trip(self):
        adapter = {class_name}()
        payload = adapter.export_state("rt-test")
        result = adapter.import_state(payload)
        assert result["agent_id"] == "rt-test"

    def test_list_agents_empty(self):
        adapter = {class_name}()
        assert adapter.list_agents() == []

    def test_list_agents_after_import(self):
        adapter = {class_name}()
        payload = StateWeavePayload(
            source_framework="test",
            metadata=AgentMetadata(agent_id="imported-agent"),
        )
        adapter.import_state(payload)
        agents = adapter.list_agents()
        assert len(agents) == 1
        assert agents[0].agent_id == "imported-agent"

    def test_validate_payload(self):
        adapter = {class_name}()
        payload = StateWeavePayload(
            source_framework="test",
            metadata=AgentMetadata(agent_id="valid-agent"),
        )
        assert adapter.validate_payload(payload) is True
'''


def generate_adapter_scaffold(
    framework_name: str,
    output_dir: str = ".",
) -> Dict[str, Any]:
    """Generate scaffold files for a new framework adapter.

    Args:
        framework_name: Name of the framework (e.g. "my_framework").
        output_dir: Root directory for output.

    Returns:
        Dict with list of generated file paths.
    """
    # Normalize
    fw_name = framework_name.lower().replace("-", "_").replace(" ", "_")
    fw_title = framework_name.replace("_", " ").replace("-", " ").title()
    fw_upper = fw_name.upper()
    class_name = fw_title.replace(" ", "") + "Adapter"

    template_vars = {
        "framework_name": fw_name,
        "framework_title": fw_title,
        "framework_upper": fw_upper,
        "class_name": class_name,
        "separator": "=" * (len(fw_title) + 60),
    }

    # Generate adapter file
    adapter_content = ADAPTER_TEMPLATE.format(**template_vars)
    adapter_path = os.path.join(output_dir, "stateweave", "adapters", f"{fw_name}_adapter.py")

    # Generate test file
    test_content = TEST_TEMPLATE.format(**template_vars)
    test_path = os.path.join(output_dir, "tests", "unit", f"test_{fw_name}_adapter.py")

    files = []

    for path, content in [(adapter_path, adapter_content), (test_path, test_content)]:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        files.append(path)
        logger.info(f"Generated: {path}")

    return {"files": files, "framework_name": fw_name, "class_name": class_name}
