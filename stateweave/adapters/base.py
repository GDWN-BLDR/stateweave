"""
StateWeave Adapter Base — ABC for all framework adapters.
===========================================================
[LAW 4] Every framework adapter MUST extend this ABC and implement
all required methods. No adapter may bypass the contract.
"""

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, List

from stateweave.schema.v1 import AgentInfo, StateWeavePayload

logger = logging.getLogger("stateweave.adapters.base")


class AdapterTier(str, Enum):
    """Support tier for framework adapters.

    TIER_1: Guaranteed stability. Maintained by core team. Breaking changes
            in the target framework are tracked and patched promptly.
    TIER_2: Actively maintained. Core team monitors for breakage but
            patches may lag behind framework releases.
    COMMUNITY: Best-effort. Contributed by the community. May break if the
               target framework changes internal state representations.
    """

    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    COMMUNITY = "community"


class AdapterError(Exception):
    """Base exception for adapter errors."""

    pass


class ExportError(AdapterError):
    """Raised when state export fails."""

    pass


class ImportError_(AdapterError):
    """Raised when state import fails.

    Named ImportError_ to avoid shadowing the builtin ImportError.
    """

    pass


class StateWeaveAdapter(ABC):
    """Abstract base class for all framework adapters.

    Every adapter translates between a framework's native state
    representation and the Universal Schema (StateWeavePayload).

    The SSOT Charter mandates:
    - All translations go TO/FROM the Universal Schema
    - No direct framework-to-framework translation
    - Non-portable state MUST be reported via non_portable_warnings[]

    Subclasses must implement:
        - framework_name: str property
        - export_state(agent_id, **kwargs) -> StateWeavePayload
        - import_state(payload, **kwargs) -> Any
        - list_agents() -> List[AgentInfo]
    """

    @property
    @abstractmethod
    def framework_name(self) -> str:
        """The name of the framework this adapter supports.

        Must be a stable identifier (e.g., "langgraph", "mcp", "crewai").
        Used in StateWeavePayload.source_framework.
        """
        ...

    @property
    @abstractmethod
    def tier(self) -> AdapterTier:
        """The support tier for this adapter.

        Determines the stability guarantee and maintenance commitment.
        See AdapterTier enum for tier definitions.
        """
        ...

    @abstractmethod
    def export_state(
        self,
        agent_id: str,
        **kwargs,
    ) -> StateWeavePayload:
        """Export an agent's cognitive state to a StateWeavePayload.

        Args:
            agent_id: Identifier of the agent to export.
            **kwargs: Framework-specific export options.

        Returns:
            A fully populated StateWeavePayload with cognitive state,
            metadata, and non-portable warnings.

        Raises:
            ExportError: If export fails.
        """
        ...

    @abstractmethod
    def import_state(
        self,
        payload: StateWeavePayload,
        **kwargs,
    ) -> Any:
        """Import a StateWeavePayload into this framework.

        Args:
            payload: The Universal Schema payload to import.
            **kwargs: Framework-specific import options.

        Returns:
            A framework-native agent reference (type varies by framework).

        Raises:
            ImportError_: If import fails.
        """
        ...

    @abstractmethod
    def list_agents(self) -> List[AgentInfo]:
        """List all agents available in this framework instance.

        Returns:
            List of AgentInfo summaries.
        """
        ...

    def validate_payload(self, payload: StateWeavePayload) -> bool:
        """Validate that a payload can be imported into this framework.

        Default implementation checks basic schema validity.
        Subclasses can override for framework-specific validation.

        Args:
            payload: The payload to validate.

        Returns:
            True if the payload is importable.
        """
        try:
            # Basic validation — payload has required fields
            if not payload.stateweave_version:
                return False
            if not payload.metadata.agent_id:
                return False
            return True
        except Exception:
            return False
