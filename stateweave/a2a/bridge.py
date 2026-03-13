"""
A2A Bridge — Agent-to-Agent Protocol integration for StateWeave.
=================================================================
Bridges the Agent2Agent (A2A) protocol with StateWeave state portability.

A2A (Google, v1.0, March 2026) defines how agents communicate.
StateWeave defines how agents transfer what they know.
This bridge connects them: when Agent A hands off to Agent B via A2A,
StateWeave serializes A's cognitive state and makes it available to B.

A2A Reference: https://a2a-protocol.org/

Key A2A concepts mapped:
- A2A Task → StateWeave export/import operation
- A2A TaskArtifact → Container for StateWeave payload
- A2A AgentCard → Extended with StateWeave capabilities
- A2A Part (DataPart) → StateWeave payload as typed data
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from stateweave.core.serializer import StateWeaveSerializer
from stateweave.schema.v1 import StateWeavePayload

logger = logging.getLogger("stateweave.a2a")

# MIME type for StateWeave payloads in A2A DataParts
STATEWEAVE_MIME_TYPE = "application/vnd.stateweave.payload+json"
STATEWEAVE_A2A_SKILL_ID = "stateweave-state-transfer"


@dataclass
class A2AAgentCapabilities:
    """StateWeave capabilities to advertise in an A2A AgentCard."""

    can_export: bool = True
    can_import: bool = True
    supported_frameworks: List[str] = field(default_factory=list)
    stateweave_version: str = ""
    encryption_supported: bool = True

    def to_agent_card_skill(self) -> Dict[str, Any]:
        """Generate an A2A AgentCard skill entry for StateWeave."""
        return {
            "id": STATEWEAVE_A2A_SKILL_ID,
            "name": "StateWeave Cognitive State Transfer",
            "description": (
                "This agent can send and receive full cognitive state "
                "(conversation history, working memory, goals, tool results) "
                "via the StateWeave universal schema."
            ),
            "tags": ["state-transfer", "cognitive-state", "portability"],
            "examples": [
                "Transfer your current knowledge to another agent",
                "Import cognitive state from a previous agent session",
            ],
            "inputModes": ["application/json"],
            "outputModes": [STATEWEAVE_MIME_TYPE, "application/json"],
            "metadata": {
                "stateweave.can_export": self.can_export,
                "stateweave.can_import": self.can_import,
                "stateweave.frameworks": self.supported_frameworks,
                "stateweave.version": self.stateweave_version,
                "stateweave.encryption": self.encryption_supported,
            },
        }


class A2ABridge:
    """Bridge between A2A protocol and StateWeave state portability.

    Enables agents communicating via A2A to transfer full cognitive state,
    not just task descriptions.
    """

    def __init__(self):
        self._serializer = StateWeaveSerializer()

    def create_transfer_artifact(
        self,
        payload: StateWeavePayload,
        artifact_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Package a StateWeave payload as an A2A TaskArtifact.

        Args:
            payload: The StateWeave payload to transfer.
            artifact_name: Optional name for the artifact.

        Returns:
            Dict conforming to A2A TaskArtifact schema.
        """
        payload_dict = self._serializer.to_dict(payload)

        artifact = {
            "name": artifact_name or f"cognitive-state-{payload.metadata.agent_id}",
            "description": (
                f"Cognitive state from {payload.source_framework} agent "
                f"'{payload.metadata.agent_id}' — "
                f"{len(payload.cognitive_state.conversation_history)} messages, "
                f"{len(payload.cognitive_state.working_memory)} memory keys"
            ),
            "parts": [
                {
                    "type": "data",
                    "mimeType": STATEWEAVE_MIME_TYPE,
                    "data": payload_dict,
                    "metadata": {
                        "stateweave_version": payload.stateweave_version,
                        "source_framework": payload.source_framework,
                        "agent_id": payload.metadata.agent_id,
                        "message_count": len(
                            payload.cognitive_state.conversation_history
                        ),
                    },
                }
            ],
            "metadata": {
                "transfer_protocol": "stateweave",
                "created_at": datetime.utcnow().isoformat(),
            },
        }

        logger.info(
            f"Created A2A transfer artifact for '{payload.metadata.agent_id}' "
            f"({len(payload.cognitive_state.conversation_history)} messages)"
        )

        return artifact

    def extract_payload(
        self,
        parts: List[Dict[str, Any]],
    ) -> Optional[StateWeavePayload]:
        """Extract a StateWeave payload from A2A message parts.

        Args:
            parts: List of A2A Part dicts from a received message/artifact.

        Returns:
            StateWeavePayload if found, None otherwise.
        """
        for part in parts:
            mime_type = part.get("mimeType", "")
            if mime_type == STATEWEAVE_MIME_TYPE:
                data = part.get("data", {})
                if data:
                    try:
                        payload = self._serializer.from_dict(data)
                        logger.info(
                            f"Extracted StateWeave payload from A2A part "
                            f"(agent: {payload.metadata.agent_id})"
                        )
                        return payload
                    except Exception as e:
                        logger.error(f"Failed to deserialize StateWeave payload: {e}")
                        return None

        logger.debug("No StateWeave payload found in A2A parts")
        return None

    def create_handoff_task(
        self,
        payload: StateWeavePayload,
        target_agent_url: str,
        task_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create an A2A Task that includes cognitive state for handoff.

        Args:
            payload: The cognitive state to include.
            target_agent_url: URL of the target agent's A2A endpoint.
            task_description: Optional description for the task.

        Returns:
            Dict conforming to A2A Task send request schema.
        """
        artifact = self.create_transfer_artifact(payload)

        task = {
            "jsonrpc": "2.0",
            "method": "tasks/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [
                        {
                            "type": "text",
                            "text": task_description or (
                                f"Continuing work from {payload.source_framework} agent "
                                f"'{payload.metadata.agent_id}'. Full cognitive state "
                                f"is attached."
                            ),
                        },
                        artifact["parts"][0],
                    ],
                },
                "metadata": {
                    "stateweave_transfer": True,
                    "source_framework": payload.source_framework,
                    "source_agent_id": payload.metadata.agent_id,
                },
            },
        }

        logger.info(
            f"Created A2A handoff task for '{payload.metadata.agent_id}' "
            f"→ {target_agent_url}"
        )

        return task

    @staticmethod
    def get_agent_capabilities(
        supported_frameworks: Optional[List[str]] = None,
    ) -> A2AAgentCapabilities:
        """Get StateWeave A2A capabilities for inclusion in AgentCard.

        Args:
            supported_frameworks: List of framework names.
                If None, auto-detects from ADAPTER_REGISTRY.

        Returns:
            A2AAgentCapabilities instance.
        """
        if supported_frameworks is None:
            from stateweave.adapters import ADAPTER_REGISTRY

            supported_frameworks = list(ADAPTER_REGISTRY.keys())

        import stateweave

        return A2AAgentCapabilities(
            can_export=True,
            can_import=True,
            supported_frameworks=supported_frameworks,
            stateweave_version=stateweave.__version__,
            encryption_supported=True,
        )
