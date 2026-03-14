# stateweave top-level __init__
"""
StateWeave — Cross-Framework Cognitive State Serializer
========================================================
Enables AI agents to migrate between frameworks while preserving
their accumulated knowledge and reasoning state.

Quick Start::

    from stateweave import (
        StateWeaveSerializer,
        MigrationEngine,
        EncryptionFacade,
        LangGraphAdapter,
        MCPAdapter,
        CrewAIAdapter,
        AutoGenAdapter,
        AdapterTier,
    )

    # Export from LangGraph
    adapter = LangGraphAdapter()
    payload = adapter.export_state("my-agent")

    # Import into MCP
    mcp = MCPAdapter()
    mcp.import_state(payload)
"""

__version__ = "0.3.1"


# Public API — Schema
from stateweave.adapters.autogen_adapter import AutoGenAdapter

# Public API — Adapters
from stateweave.adapters.base import AdapterTier, StateWeaveAdapter
from stateweave.adapters.crewai_adapter import CrewAIAdapter
from stateweave.adapters.langgraph_adapter import LangGraphAdapter
from stateweave.adapters.mcp_adapter import MCPAdapter
from stateweave.core.diff import StateDiff, diff_payloads
from stateweave.core.encryption import EncryptionFacade
from stateweave.core.migration import MigrationEngine
from stateweave.core.portability import PortabilityAnalyzer

# Public API — Core
from stateweave.core.serializer import StateWeaveSerializer
from stateweave.schema.v1 import (
    AgentInfo,
    AgentMetadata,
    AuditEntry,
    CognitiveState,
    Message,
    MessageRole,
    NonPortableWarning,
    StateWeavePayload,
)

# Public API — Schema Validation
from stateweave.schema.validator import get_schema_json, validate_payload

__all__ = [
    # Version
    "__version__",
    # Schema
    "StateWeavePayload",
    "CognitiveState",
    "Message",
    "MessageRole",
    "AgentMetadata",
    "AgentInfo",
    "AuditEntry",
    "NonPortableWarning",
    # Core
    "StateWeaveSerializer",
    "EncryptionFacade",
    "MigrationEngine",
    "diff_payloads",
    "StateDiff",
    "PortabilityAnalyzer",
    # Adapters
    "AdapterTier",
    "StateWeaveAdapter",
    "LangGraphAdapter",
    "MCPAdapter",
    "CrewAIAdapter",
    "AutoGenAdapter",
    # Validation
    "get_schema_json",
    "validate_payload",
]
