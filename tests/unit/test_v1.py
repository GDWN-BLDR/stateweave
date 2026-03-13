"""
Unit Tests: Schema v1 Models (extended)
==========================================
Additional tests for full v1 model coverage.
"""

from stateweave.schema.v1 import (
    SCHEMA_VERSION,
    AccessPolicy,
    AgentInfo,
    AgentMetadata,
    AuditAction,
    AuditEntry,
    EncryptionInfo,
)


class TestV1ExtendedModels:
    def test_agent_info(self):
        info = AgentInfo(agent_id="a1", framework="langgraph")
        assert info.agent_id == "a1"
        assert info.state_size_bytes is None

    def test_agent_metadata_policies(self):
        meta = AgentMetadata(
            agent_id="m1",
            access_policy=AccessPolicy.SHARED,
            tags=["test", "dev"],
        )
        assert meta.access_policy == AccessPolicy.SHARED
        assert len(meta.tags) == 2

    def test_audit_entry_actions(self):
        for action in AuditAction:
            entry = AuditEntry(action=action, success=True)
            assert entry.action == action

    def test_encryption_info_defaults(self):
        info = EncryptionInfo()
        assert info.algorithm == "AES-256-GCM"
        assert info.encrypted is False

    def test_schema_version_constant(self):
        assert SCHEMA_VERSION == "0.2.0"
