"""
Universal Schema v1 — Pydantic Models for Cognitive State
==========================================================
[BOARD 2026-03-13] The Single Source of Truth for agent state representation.

All cognitive state transiting between frameworks MUST conform to these models.
Schema versions are immutable — new versions are additive, never destructive.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("stateweave.schema.v1")

SCHEMA_VERSION = "0.2.0"


class MessageRole(str, Enum):
    """Supported message roles across frameworks."""

    HUMAN = "human"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
    FUNCTION = "function"


class Message(BaseModel):
    """A single message in conversation history."""

    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[datetime] = None


class GoalNode(BaseModel):
    """A node in the agent's goal tree."""

    goal_id: str
    description: str
    status: str = "pending"  # pending, active, completed, failed
    parent_id: Optional[str] = None
    children: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Cached result from a tool invocation."""

    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    result_hash: Optional[str] = None
    timestamp: Optional[datetime] = None
    success: bool = True
    error: Optional[str] = None


class CognitiveState(BaseModel):
    """The core cognitive state of an AI agent.

    This represents everything the agent "knows" and "thinks" —
    the accumulated knowledge, reasoning state, and decision context.
    """

    conversation_history: List[Message] = Field(default_factory=list)
    working_memory: Dict[str, Any] = Field(default_factory=dict)
    goal_tree: Dict[str, GoalNode] = Field(default_factory=dict)
    tool_results_cache: Dict[str, ToolResult] = Field(default_factory=dict)
    trust_parameters: Dict[str, float] = Field(default_factory=dict)
    long_term_memory: Dict[str, Any] = Field(default_factory=dict)
    episodic_memory: List[Dict[str, Any]] = Field(default_factory=list)
    framework_specific: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Framework-native state that doesn't map to universal fields. "
            "Preserved during round-trips to the same framework. Enables "
            "zero-loss translation when source == target framework."
        ),
    )


class NonPortableWarningSeverity(str, Enum):
    """Severity levels for non-portable state warnings."""

    INFO = "INFO"
    WARN = "WARN"
    CRITICAL = "CRITICAL"


class NonPortableWarning(BaseModel):
    """Warning about state that could not be fully transferred."""

    field: str
    reason: str
    severity: NonPortableWarningSeverity = NonPortableWarningSeverity.WARN
    data_loss: bool = False
    recommendation: Optional[str] = None
    original_type: Optional[str] = None


class AuditAction(str, Enum):
    """Types of audit trail actions."""

    EXPORT = "export"
    IMPORT = "import"
    MIGRATE = "migrate"
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"
    VALIDATE = "validate"
    DIFF = "diff"
    TOOL_CALL = "tool_call"
    STATE_UPDATE = "state_update"


class AuditEntry(BaseModel):
    """A single entry in the audit trail."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: AuditAction
    agent: Optional[str] = None
    framework: Optional[str] = None
    success: bool = True
    details: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class AccessPolicy(str, Enum):
    """Access policies for state payloads."""

    PRIVATE = "private"
    SHARED = "shared"
    PUBLIC = "public"
    RESTRICTED = "restricted"


class AgentMetadata(BaseModel):
    """Metadata about the agent whose state is being transferred."""

    agent_id: str
    agent_name: Optional[str] = None
    owner: Optional[str] = None
    namespace: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    access_policy: AccessPolicy = AccessPolicy.PRIVATE
    framework_capabilities: Dict[str, Any] = Field(default_factory=dict)
    custom_metadata: Dict[str, Any] = Field(default_factory=dict)


class EncryptionInfo(BaseModel):
    """Metadata about encryption applied to the payload."""

    algorithm: str = "AES-256-GCM"
    key_id: Optional[str] = None
    encrypted: bool = False
    nonce: Optional[str] = None


class PayloadSignature(BaseModel):
    """Digital signature for payload authenticity verification.

    Allows the receiver to verify that the payload was created by a
    trusted sender and has not been tampered with in transit.
    """

    algorithm: str = "Ed25519"
    public_key_id: str = Field(description="Identifier for the public key used to verify")
    signature_b64: str = Field(description="Base64-encoded signature of the serialized payload")
    signed_at: datetime = Field(default_factory=datetime.utcnow)


class StateWeavePayload(BaseModel):
    """The Universal Schema — the canonical representation of agent cognitive state.

    This is the SSOT. All adapters translate TO and FROM this format.
    Direct framework-to-framework translation is forbidden (SSOT Charter).

    Attributes:
        stateweave_version: Schema version (semver). Immutable per version.
        source_framework: The framework this state was exported from.
        source_version: Version of the source framework.
        exported_at: ISO-8601 timestamp of export.
        cognitive_state: The agent's cognitive state (memories, goals, etc.).
        metadata: Agent identification and ownership metadata.
        audit_trail: History of operations performed on this state.
        non_portable_warnings: Explicit list of state that couldn't transfer.
        encryption: Encryption metadata (if payload is encrypted).
    """

    stateweave_version: str = Field(default=SCHEMA_VERSION)
    source_framework: str
    source_version: Optional[str] = None
    exported_at: datetime = Field(default_factory=datetime.utcnow)
    cognitive_state: CognitiveState = Field(default_factory=CognitiveState)
    metadata: AgentMetadata
    audit_trail: List[AuditEntry] = Field(default_factory=list)
    non_portable_warnings: List[NonPortableWarning] = Field(default_factory=list)
    encryption: EncryptionInfo = Field(default_factory=EncryptionInfo)
    signature: Optional[PayloadSignature] = None

    @field_validator("stateweave_version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate version is a valid semver-like string."""
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError(f"Version must be semver (X.Y.Z), got: {v}")
        for part in parts:
            if not part.isdigit():
                raise ValueError(f"Version parts must be numeric, got: {v}")
        return v


class AgentInfo(BaseModel):
    """Summary information about an agent (used by adapter.list_agents())."""

    agent_id: str
    agent_name: Optional[str] = None
    framework: str
    state_size_bytes: Optional[int] = None
    last_active: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
